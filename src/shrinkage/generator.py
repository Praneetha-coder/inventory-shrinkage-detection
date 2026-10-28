"""Deterministic synthetic data generator (fixed seed, scale-parameterised).

Core modelling idea
-------------------
Two stock timelines are kept for every store/SKU pair ("pair"):
  * BOOK     = opening + sum(quantity_signed of recorded movements, by posted_ts)
  * PHYSICAL = opening + physical effect of movements (by movement_ts) + UNRECORDED events (hidden losses)
A cycle count observes PHYSICAL (+ small miscount noise) and is compared with BOOK as-of count_ts.
Therefore every variance is *derived* and exactly decomposable into causes (ground_truth_count_causes.csv).
Planted anomalies are created by reserving rows from the baseline budget of the matching type, rewriting
them, and recording a labelled ground-truth case: unrelated rows are never silently corrupted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config, OPEN, SPLIT, CLOSE, DAY
from . import schema as S

# movement type codes
T_SALE, T_RECV, T_XOUT, T_XIN, T_ADJ, T_DMG, T_RET = range(7)
MT = S.MOVEMENT_TYPES
ROLE_LOCAL = ["STORE_MANAGER", "ASSISTANT_MANAGER", "CASHIER", "CASHIER", "CASHIER", "STOCK_CLERK", "STOCK_CLERK", "STOCK_CLERK"]
# slot -> who acts: 0 manager-level (authorised to adjust), 1 cashier, 2 stock clerk
CATS = [  # name, cost median, sigma, case sizes, popularity, margin lo/hi, perishable
    ("ELECTRONICS", 45, .8, (4, 6), .5, 1.15, 1.45, 0), ("GROCERY", 3, .5, (12, 24), 2.0, 1.2, 1.6, 1),
    ("BEAUTY", 9, .6, (6, 12), 1.0, 1.4, 2.0, 0), ("APPAREL", 14, .6, (6, 10), .8, 1.6, 2.2, 0),
    ("HOUSEHOLD", 7, .6, (6, 12), 1.0, 1.3, 1.8, 0), ("TOYS", 11, .6, (6, 12), .7, 1.4, 1.9, 0),
    ("PHARMACY_OTC", 5, .5, (12, 12), 1.2, 1.3, 1.7, 0), ("ALCOHOL_TOBACCO", 12, .5, (12, 24), 1.0, 1.15, 1.35, 0),
    ("SPORTS", 20, .7, (4, 8), .5, 1.4, 1.9, 0), ("HARDWARE", 8, .6, (6, 12), .8, 1.3, 1.8, 0),
    ("BABY", 8, .5, (6, 12), .9, 1.3, 1.7, 0), ("PET", 6, .5, (6, 12), .9, 1.3, 1.7, 1)]
WEEKDAY_MULT = np.array([.9, .9, .95, 1.0, 1.15, 1.35, 1.25])  # Mon..Sun


# ----------------------------------------------------------------------------- helpers
def ids(prefix, nums, width):
    return np.char.add(prefix, np.char.zfill(np.asarray(nums).astype(np.int64).astype(str), width))


def emp_local_v(day, st, slot):
    """Deterministic rotation: which of the store's 8 employees works (day, shift type, slot)."""
    day, st, slot = np.asarray(day), np.asarray(st), np.asarray(slot)
    return np.where(slot == 0, (day + st) % 2, np.where(slot == 1, 2 + (day + st) % 3, 5 + (day + 2 * st) % 3))


def times_for_emp(rng, local, n, day_lo, day_hi):
    """Timestamps (sec) at which a specific employee is on shift (so planted patterns are attributable)."""
    slot = 0 if local < 2 else (1 if local < 5 else 2)
    combos = [(d, s) for d in range(day_lo, day_hi + 1) for s in (0, 1) if int(emp_local_v(d, s, slot)) == local]
    sel = rng.integers(0, len(combos), n)
    d = np.array([combos[i][0] for i in sel]); s = np.array([combos[i][1] for i in sel])
    return d * DAY + OPEN + s * 8 * 3600 + rng.integers(0, 8 * 3600 - 1, n)


class PrefixSum:
    """Sum of val for events of a pair with ts <= T (vectorised point queries)."""
    BIG = 1 << 27

    def __init__(self, pair, ts, val):
        key = pair.astype(np.int64) * self.BIG + ts.astype(np.int64)
        o = np.argsort(key, kind="stable")
        self.k = key[o]
        self.c = np.concatenate([[0], np.cumsum(val[o].astype(np.int64))])

    def q(self, pair, T):
        pair = pair.astype(np.int64)
        hi = np.searchsorted(self.k, pair * self.BIG + T.astype(np.int64), side="right")
        lo = np.searchsorted(self.k, pair * self.BIG, side="left")
        return self.c[hi] - self.c[lo]


def min_running(pair, ts, val, n):
    """Per-pair minimum of the running sum (<=0); positives first on timestamp ties."""
    o = np.lexsort((-val, ts, pair))
    p, v = pair[o], val[o].astype(np.int64)
    c = np.cumsum(v)
    first = np.r_[True, p[1:] != p[:-1]]
    starts = np.flatnonzero(first)
    base = np.r_[0, c[:-1]][starts]
    run = c - base[np.cumsum(first) - 1]
    out = np.zeros(n, dtype=np.int64)
    out[p[starts]] = np.minimum(np.minimum.reduceat(run, starts), 0)
    return out


# ----------------------------------------------------------------------------- generator
def generate(cfg: Config) -> dict:
    rng = np.random.default_rng(cfg.seed)
    D, NS, NK, N = cfg.days, cfg.n_stores, cfg.n_skus, cfg.n_movements
    d0 = np.datetime64(cfg.start_date, "D")
    T0 = np.datetime64(cfg.start_date, "s")
    wd0 = pd.Timestamp(cfg.start_date).dayofweek

    def dstr(dayidx):  # day offsets -> 'YYYY-MM-DD'
        return (d0 + np.asarray(dayidx).astype("timedelta64[D]")).astype(str)

    def tstr(sec):  # seconds since start -> 'YYYY-MM-DD HH:MM:SS'
        return np.char.replace((T0 + np.asarray(sec, dtype=np.int64).astype("timedelta64[s]")).astype(str), "T", " ")

    def sec_open(n):  # intraday time with an evening peak, inside opening hours
        peak = rng.random(n) < .45
        return np.where(peak, np.clip(rng.normal(17 * 3600, 2.2 * 3600, n), OPEN, CLOSE - 1),
                        rng.integers(OPEN, CLOSE, n)).astype(np.int64)

    # ------------------------------------------------------------------ 1. master data
    is_wh = np.zeros(NS, bool)
    is_wh[np.unique(np.linspace(0, NS - 1, max(1, round(.04 * NS))).astype(int))] = True
    size = np.where(is_wh, 1.0, rng.lognormal(0, .35, NS))
    region = np.array(S.REGIONS)[np.arange(NS) % 5]
    fmt = np.where(is_wh, "DISTRIBUTION_CENTER", np.where(size < .8, "EXPRESS", np.where(size > 1.25, "SUPERSTORE", "STANDARD")))
    open_off = -rng.integers(200, 2500, NS)
    stores = pd.DataFrame({
        "store_id": ids("STORE-", np.arange(1, NS + 1), 6),
        "store_name": [f"{region[i].title()} {'Warehouse' if is_wh[i] else 'Store'} {i + 1:03d}" for i in range(NS)],
        "store_type": np.where(is_wh, "WAREHOUSE", "STORE"), "store_format": fmt, "region": region,
        "open_date": dstr(open_off), "status": "ACTIVE", "effective_from": dstr(open_off), "effective_to": None})

    cat_i = rng.integers(0, len(CATS), NK)
    A = lambda j: np.array([c[j] for c in CATS])
    cost = np.round(np.clip(np.exp(np.log(A(1)[cat_i]) + A(2)[cat_i] * rng.standard_normal(NK)), .5, 900), 2)
    price = np.round(np.maximum(cost * rng.uniform(A(5)[cat_i], A(6)[cat_i]), cost + .05), 2)
    case_qty = np.where(rng.random(NK) < .5, np.array([CATS[i][3][0] for i in cat_i]), np.array([CATS[i][3][1] for i in cat_i]))
    pop = rng.lognormal(0, .9, NK) * A(4)[cat_i]
    perish = A(7)[cat_i].astype(int)
    cat_names = np.array([c[0] for c in CATS])[cat_i]
    skus = pd.DataFrame({
        "sku_id": ids("SKU-", np.arange(1, NK + 1), 6),
        "sku_name": [f"{cat_names[i].title().replace('_', ' ')} Item {i + 1:05d}" for i in range(NK)],
        "category": cat_names, "unit_cost": cost, "unit_price": price, "case_qty": case_qty.astype(int),
        "is_perishable": perish, "launch_date": dstr(-rng.integers(60, 2500, NK)), "status": "ACTIVE"})

    # employees: 8 per store (2 manager-level, 3 cashiers, 3 stock clerks) + HQ
    n_es = NS * 8
    n_ops, n_an = max(2, NS // 20), max(2, NS // 25)
    n_emp = n_es + n_ops + n_an
    hire_off = -rng.integers(40, 1800, n_emp)
    emp_ids = ids("EMP-", np.arange(1, n_emp + 1), 6)
    store_ids = stores.store_id.values
    employees = pd.DataFrame({
        "employee_id": emp_ids, "home_store_id": np.r_[np.repeat(store_ids, 8), [None] * (n_ops + n_an)],
        "hire_date": dstr(hire_off), "employment_status": "ACTIVE"})
    roles = []   # (employee, store, role, can_adjust, can_count, can_investigate, effective_from_day, effective_to_day|None)
    for e in range(n_emp):
        if e < n_es:
            code, sid = ROLE_LOCAL[e % 8], store_ids[e // 8]
            if code in ("CASHIER", "STOCK_CLERK") and rng.random() < .10:   # trainee promoted on window start -> role history
                roles.append((emp_ids[e], sid, "TRAINEE", 0, 0, 0, int(hire_off[e]), -1))
                roles.append((emp_ids[e], sid, code, 0, int(code == "STOCK_CLERK"), 0, 0, None))
            else:
                roles.append((emp_ids[e], sid, code, int(code in ("STORE_MANAGER", "ASSISTANT_MANAGER")),
                              int(code != "CASHIER"), 0, int(hire_off[e]), None))
        elif e < n_es + n_ops:
            roles.append((emp_ids[e], None, "OPERATIONS_MANAGER", 0, 0, 1, int(hire_off[e]), None))
        else:
            roles.append((emp_ids[e], None, "MERCH_ANALYST", 0, 0, 0, int(hire_off[e]), None))
    employee_roles = pd.DataFrame({
        "employee_role_id": ids("ERL-", np.arange(1, len(roles) + 1), 6), "employee_id": [r[0] for r in roles],
        "store_id": [r[1] for r in roles], "role_code": [r[2] for r in roles], "can_adjust_inventory": [r[3] for r in roles],
        "can_perform_counts": [r[4] for r in roles], "can_investigate": [r[5] for r in roles],
        "effective_from": dstr([r[6] for r in roles]),
        "effective_to": [None if r[7] is None else str(dstr(r[7])) for r in roles]})
    ops_ids = emp_ids[n_es:n_es + n_ops]
    analyst_ids = emp_ids[n_es + n_ops:]

    # shifts: S x D x 2 x 3 slots, employee by deterministic rotation
    si = np.arange(NS * D * 2 * 3)
    sh_slot, sh_st, sh_day, sh_store = si % 3, (si // 3) % 2, (si // 6) % D, si // (6 * D)
    sh_local = emp_local_v(sh_day, sh_st, sh_slot)
    sh_start = sh_day * DAY + OPEN + sh_st * 8 * 3600
    shifts = pd.DataFrame({
        "shift_id": ids("SHIFT-", si + 1, 7), "store_id": store_ids[sh_store], "employee_id": emp_ids[sh_store * 8 + sh_local],
        "shift_date": dstr(sh_day), "shift_type": np.where(sh_st == 0, "DAY", "EVENING"),
        "role_on_shift": np.array(ROLE_LOCAL)[sh_local], "start_ts": tstr(sh_start), "end_ts": tstr(sh_start + 8 * 3600),
        "status": "COMPLETED"})
    del si, sh_slot, sh_st, sh_day, sh_store, sh_local, sh_start

    # assortment (Store N:M SKU bridge)
    ps = [np.sort(rng.choice(NK, min(NK, (2 if is_wh[s] else 1) * cfg.skus_per_store), replace=False)) for s in range(NS)]
    lens = np.array([len(x) for x in ps])
    pair_sku, pair_store = np.concatenate(ps), np.repeat(np.arange(NS), lens)
    store_start = np.r_[0, np.cumsum(lens)]
    NP = len(pair_sku)
    pcost, pprice, pcase = cost[pair_sku], price[pair_sku], case_qty[pair_sku]
    base_w = pop[pair_sku] * size[pair_store]
    wh_p = is_wh[pair_store]
    sale_w = np.where(wh_p, 0, base_w)
    recv_w = np.where(wh_p, base_w * 8, base_w)
    xfer_w = np.where(wh_p, base_w * 6, base_w)
    sku_cnt = np.bincount(pair_sku, minlength=NK)
    sku_order = np.argsort(pair_sku, kind="stable")
    sku_start = np.r_[0, np.cumsum(sku_cnt)]
    inv_order = np.empty(NP, np.int64); inv_order[sku_order] = np.arange(NP)

    def other_pair_same_sku(p, retail_only=False):
        """A different store/pair that carries the same SKU (vectorised)."""
        out = np.full(len(p), -1, np.int64)
        todo = np.arange(len(p))
        for _ in range(12):
            if not len(todo):
                break
            s = pair_sku[p[todo]]; c = sku_cnt[s]
            ok = c >= 2
            todo, s, c = todo[ok], s[ok], c[ok]
            r = rng.integers(0, c - 1)
            r = r + (r >= inv_order[p[todo]] - sku_start[s])
            cand = sku_order[sku_start[s] + r]
            good = ~(wh_p[cand] if retail_only else np.zeros(len(cand), bool))
            out[todo[good]] = cand[good]
            todo = todo[~good]
        return out

    # promotions (+ bridge); each SKU has up to 2 non-overlapping promo windows
    n_pr = max(3, NK // 50)
    p_id = np.full((NK, 2), -1); p_s = np.zeros((NK, 2), int); p_e = np.zeros((NK, 2), int)
    pr_rows, br_rows = [], []
    for j in range(n_pr):
        s0 = int(rng.integers(0, D - 8)); e0 = min(D - 1, s0 + int(rng.integers(7, 29)))
        k = int(rng.integers(5, max(6, NK // 100)))
        for sk in rng.choice(NK, k, replace=False):
            for sl in (0, 1):
                if p_id[sk, sl] < 0 and (sl == 0 or e0 < p_s[sk, 0] or s0 > p_e[sk, 0]):
                    p_id[sk, sl], p_s[sk, sl], p_e[sk, sl] = j, s0, e0
                    br_rows.append((j, sk)); break
        pr_rows.append((j, int(rng.choice([10, 15, 20, 25, 30, 40])), s0, e0, rng.choice(analyst_ids)))
    disc = np.array([r[1] for r in pr_rows])
    promotions = pd.DataFrame({
        "promotion_id": ids("PROMO-", np.arange(1, n_pr + 1), 6),
        "promotion_name": [f"Promo {j + 1:03d} ({r[1]}% off)" for j, r in enumerate(pr_rows)],
        "discount_pct": disc, "start_date": dstr([r[2] for r in pr_rows]), "end_date": dstr([r[3] for r in pr_rows]),
        "status": "ENDED", "owner_employee_id": [r[4] for r in pr_rows]})
    promotion_skus = pd.DataFrame({"promotion_id": ids("PROMO-", np.array([b[0] for b in br_rows]) + 1, 6),
                                   "sku_id": ids("SKU-", np.array([b[1] for b in br_rows]) + 1, 6)})

    # ------------------------------------------------------------------ 2. baseline events (budget by type)
    n_sale, n_recv, n_x, n_adj, n_dmg = round(.76 * N), round(.07 * N), round(.045 * N), round(.006 * N), round(.015 * N)
    n_ret = N - n_sale - n_recv - 2 * n_x - n_adj - n_dmg
    assert n_ret > 0
    dw = WEEKDAY_MULT[(wd0 + np.arange(D)) % 7]; dayp = dw / dw.sum()

    # SALES (with promotion surges)
    sp = rng.choice(NP, n_sale, p=sale_w / sale_w.sum())
    sday = rng.choice(D, n_sale, p=dayp)
    ssku = pair_sku[sp]
    surge = (p_id[ssku, 0] >= 0) & (rng.random(n_sale) < .5)
    a, b = p_s[ssku, 0], p_e[ssku, 0]
    sday = np.where(surge, a + (rng.random(n_sale) * (b - a + 1)).astype(int), sday)
    spromo = np.full(n_sale, -1)
    for sl in (1, 0):
        m = (p_id[ssku, sl] >= 0) & (sday >= p_s[ssku, sl]) & (sday <= p_e[ssku, sl])
        spromo[m] = p_id[ssku[m], sl]
    sqty = 1 + rng.poisson(.5, n_sale) + ((spromo >= 0) & (rng.random(n_sale) < .3))
    sts = sday * DAY + sec_open(n_sale)

    # RECEIPTS
    rp = rng.choice(NP, n_recv, p=recv_w / recv_w.sum())
    rq = pcase[rp] * (1 + rng.poisson(.4 + 2 * wh_p[rp]))
    rts = rng.integers(0, D, n_recv) * DAY + rng.integers(OPEN, SPLIT, n_recv)

    # TRANSFERS (out at source now, in at destination 1-3 days later)
    w = xfer_w * (sku_cnt[pair_sku] >= 2)
    xs = rng.choice(NP, n_x, p=w / w.sum())
    xd = other_pair_same_sku(xs)
    assert (xd >= 0).all()
    xq = pcase[xs] * (1 + rng.poisson(.5, n_x))
    xday = rng.integers(0, D - 4, n_x)
    xts_out = xday * DAY + sec_open(n_x)
    xts_in = (xday + rng.integers(1, 4, n_x)) * DAY + sec_open(n_x)

    # ADJUSTMENTS (legit; the book change is the correction of an earlier unrecorded physical drift)
    ap = rng.choice(NP, n_adj, p=recv_w / recv_w.sum())
    aneg = rng.random(n_adj) < .85
    aqty = np.where(aneg, -(1 + np.minimum(rng.poisson(.8, n_adj), 3)), 1 + np.minimum(rng.poisson(.6, n_adj), 3))
    areason = np.where(aneg, rng.choice(["COUNT_CORRECTION", "DATA_ENTRY_FIX", "SYSTEM_ERROR", "EXPIRED"], n_adj, p=[.5, .2, .2, .1]),
                       rng.choice(["FOUND_STOCK", "COUNT_CORRECTION", "DATA_ENTRY_FIX"], n_adj, p=[.6, .3, .1])).astype(object)
    ats = rng.integers(0, D, n_adj) * DAY + sec_open(n_adj)

    # DAMAGE (recorded, legit)
    dp = rng.choice(NP, n_dmg, p=recv_w / recv_w.sum())
    dqty = -(1 + np.minimum(rng.poisson(.7, n_dmg), 4))
    dreason = rng.choice(S.DMG_REASONS[:5], n_dmg, p=[.3, .25, .2, .15, .1]).astype(object)
    dts = rng.integers(0, D, n_dmg) * DAY + sec_open(n_dmg)

    # CUSTOMER RETURNS linked to an earlier sale (+ a few legit no-receipt returns approved by a manager)
    pool = np.flatnonzero(sday <= D - 16)
    n_nr = round(.01 * n_ret); n_link = n_ret - n_nr
    n_wo = round(.2 * n_ret)
    assert len(pool) >= n_link + n_wo, "scale too small for returns"
    sel = rng.choice(pool, n_link, replace=False)
    wo = rng.choice(np.setdiff1d(pool, sel), n_wo, replace=False)
    rr_pair = np.r_[sp[sel], rng.choice(NP, n_nr, p=sale_w / sale_w.sum())]
    rr_qty = np.r_[np.minimum(sqty[sel], np.where(rng.random(n_link) < .85, 1, 2)), np.ones(n_nr, int)]
    rr_ts = np.r_[(sday[sel] + rng.integers(1, 15, n_link)) * DAY, rng.integers(0, D, n_nr) * DAY] + sec_open(n_ret)
    rr_orig = np.r_[sel, np.full(n_nr, -1)]
    rr_kind = np.r_[np.zeros(n_link, int), np.ones(n_nr, int)]           # 0 linked, 1 legit no-receipt, 2 phantom
    rr_reason = np.r_[rng.choice(["CHANGE_OF_MIND", "WRONG_ITEM"], n_link, p=[.78, .22]), np.full(n_nr, "NO_RECEIPT")].astype(object)
    rr_noappr = np.r_[np.zeros(n_link, bool), rng.random(n_nr) < .10]    # 10% of legit no-receipt lack an approver

    # ---- assemble movement arrays (creation order) -----
    off = {}; parts = []

    def add(name, typ, pair, tpair, qty, phys, ts, slot, reason=None, promo=None, xf=None, cp=None):
        n = len(pair)
        off[name] = (sum(len(p[0]) for p in parts), sum(len(p[0]) for p in parts) + n)
        parts.append((np.full(n, typ), pair, tpair, qty, phys, ts, np.full(n, slot) if np.isscalar(slot) else slot,
                      np.full(n, None, object) if reason is None else reason,
                      np.full(n, -1) if promo is None else promo, np.full(n, -1) if xf is None else xf,
                      np.full(n, -1) if cp is None else cp))
    add("sale", T_SALE, sp, sp, -sqty, -sqty, sts, 1, promo=spromo)
    add("recv", T_RECV, rp, rp, rq, rq, rts, 2)
    xi = np.arange(n_x)
    add("xout", T_XOUT, xs, xs, -xq, -xq, xts_out, 2, xf=xi, cp=pair_store[xd])
    add("xin", T_XIN, xd, xd, xq, xq, xts_in, 2, xf=xi, cp=pair_store[xs])
    add("adj", T_ADJ, ap, ap, aqty, np.zeros(n_adj, int), ats, 0, reason=areason)
    add("dmg", T_DMG, dp, dp, dqty, dqty, dts, 2, reason=dreason)
    add("ret", T_RET, rr_pair, rr_pair, rr_qty, rr_qty, rr_ts, 1, reason=rr_reason)
    typ, pair, tpair, qty, phys, ts, slot, reason, promo, xfer, cp = [np.concatenate([p[i] for p in parts]) for i in range(11)]
    reason = reason.astype(object)
    M = len(typ); assert M == N
    posted = ts.copy()
    note = np.full(M, None, object)
    locked = np.zeros(M, bool)
    drift = np.zeros(M, bool); drift[off["adj"][0]:off["adj"][1]] = True   # legit adjustment => earlier unrecorded drift
    ro = off["ret"][0]
    so = off["sale"][0]
    del parts

    # hidden (unrecorded physical) events: cause 0 background, 1 pre-adjustment drift, 2 unexplained loss
    hid_pair, hid_ts, hid_qty, hid_cause = [], [], [], []

    def hid_add(p, t, q, c):
        hid_pair.append(np.atleast_1d(p)); hid_ts.append(np.atleast_1d(t)); hid_qty.append(np.atleast_1d(q))
        hid_cause.append(np.full(len(np.atleast_1d(p)), c))
    n_bg = round(.04 * NP)
    bgp = rng.choice(NP, n_bg, p=base_w / base_w.sum())
    hid_add(bgp, rng.integers(0, D * DAY, n_bg), -np.where(rng.random(n_bg) < .85, 1, 2), 0)

    # ------------------------------------------------------------------ 3. planted anomalies (labelled)
    cases, pc = [], dict(pair=[], actual=[], rec=[], entered=[], case=[])   # planned cycle counts

    def new_case(issue, group, expected, store, sku=None, emp=None, t0=0, t1=0, units=0, value=0.0, detect=1, desc="",
                 mov=(), cnt=(), xfer=(), pairs=()):
        cases.append(dict(issue_type=issue, case_group=group, store=int(store), sku=sku, emp=emp, t0=int(t0), t1=int(t1),
                          expected=expected, units=int(units), value=round(float(value), 2), detectable=int(detect),
                          desc=desc, mov=list(map(int, mov)), cnt=list(cnt), xfer=list(map(int, xfer)), pairs=list(map(int, pairs))))
        return len(cases) - 1

    def plan_count(p, actual, rec, case_i, entered=None):
        pc["pair"].append(int(p)); pc["actual"].append(int(actual)); pc["rec"].append(int(rec))
        pc["entered"].append(-1 if entered is None else int(entered)); pc["case"].append(case_i)
        return len(pc["pair"]) - 1

    def free(t, extra=None):
        m = (typ == t) & ~locked
        return np.flatnonzero(m if extra is None else m & extra)

    retail = np.flatnonzero(~is_wh)
    perm = rng.permutation(retail)
    cursor = [0]

    def next_store():
        s = perm[cursor[0] % len(perm)]; cursor[0] += 1; return int(s)

    def store_pairs(s, min_cost=0.0, k_min=1):
        c = np.arange(store_start[s], store_start[s + 1])
        good = c[pcost[c] >= min_cost]
        return good if len(good) >= k_min else c[np.argsort(-pcost[c])[:max(k_min, 20)]]

    n_ul = max(3, round(.12 * NS)); n_ra = max(3, round(.10 * NS)); n_rr = max(2, round(.06 * NS))
    n_ld = max(3, round(.08 * NS)); n_xt = max(4, round(.00125 * cfg.n_counts)); n_tp = max(5, round(.0015 * cfg.n_counts))
    n_ws = max(6, round(.0004 * N)); n_nrs = max(8, round(.01 * n_adj)); n_ua = max(5, round(.01 * n_adj))

    # (a) benign trap: legitimate documented damage event (looks like a big write-off)
    for _ in range(n_ld):
        s = next_store(); k = int(rng.integers(8, 13)); pp = rng.choice(store_pairs(s, 8, k), k, replace=False)
        rows = rng.choice(free(T_DMG), k, replace=False)
        q = -rng.integers(3, 7, k)
        while (-q * pcost[pp]).sum() < 450: q -= 1
        day = int(rng.integers(5, D - 5)); t = day * DAY + OPEN + 2 * 3600 + np.arange(k) * 120 + rng.integers(0, 3600)
        pair[rows] = pp; tpair[rows] = pp; qty[rows] = q; phys[rows] = q; ts[rows] = t; posted[rows] = t; slot[rows] = 0
        reason[rows] = rng.choice(["WATER_DAMAGE", "POWER_OUTAGE_SPOILAGE", "DAMAGED_IN_TRANSIT"])
        note[rows] = f"INC-{s + 1:06d}-{day:03d}"; locked[rows] = True
        new_case("LEGIT_DAMAGE_EVENT", "BENIGN_EXPLANATION", "AUTO_CLOSE_BENIGN", s, t0=t.min(), t1=t.max(), units=0, value=0,
                 desc=f"Documented incident {note[rows[0]]}: {k} SKUs written off with reason and manager approval; stock genuinely damaged and recorded.",
                 mov=rows)

    # (b) planted theft: unexplained (unrecorded) loss on high-value SKUs, revealed only by cycle counts
    for _ in range(n_ul):
        s = next_store(); k = min(int(rng.integers(6, 13)), 20); pp = rng.choice(store_pairs(s, 8, k), k, replace=False)
        a0 = int(rng.integers(10, D - 50)); a1 = min(a0 + int(rng.integers(14, 36)), D - 12)
        ci = new_case("UNEXPLAINED_LOSS", "PLANTED_THEFT_PATTERN", "INVESTIGATE", s, t0=a0 * DAY, t1=a1 * DAY,
                      desc="Unrecorded stock disappearance over several weeks; no movement, adjustment or damage explains it.", pairs=pp)
        tot_u = tot_v = 0; det = 0
        for p in pp:
            ne = int(rng.integers(3, 9)); q = -(1 + np.minimum(rng.poisson(1.0, ne), 4))
            if q.sum() > -6: q[0] -= 6 + q.sum()
            hid_add(np.full(ne, p), rng.integers(a0 * DAY, a1 * DAY, ne), q, 2)
            tot_u += -q.sum(); tot_v += -q.sum() * pcost[p]
            if rng.random() < .85:
                ca = (a1 + int(rng.integers(1, 10))) * DAY + int(rng.integers(OPEN, CLOSE - 3600))
                cases[ci]["cnt"].append(plan_count(p, ca, ca, ci)); det = 1
        cases[ci].update(units=tot_u, value=round(tot_v, 2), detectable=det)

    # (c) planted theft: repeated negative adjustments by one manager-level employee, concealing physical loss
    for _ in range(n_ra):
        s = next_store(); loc = int(rng.integers(0, 2)); emp = s * 8 + loc
        favored = rng.choice(store_pairs(s, 8, 5), int(rng.integers(3, 6)), replace=False)
        n = int(rng.integers(12, 23)); rows = rng.choice(free(T_ADJ), n, replace=False)
        a0 = int(rng.integers(10, D - 25)); t = times_for_emp(rng, loc, n, a0, a0 + 12)
        pp = favored[np.r_[np.arange(len(favored)), rng.integers(0, len(favored), n - len(favored))][:n]]
        q = -rng.integers(2, 7, n)
        pair[rows] = pp; tpair[rows] = pp; qty[rows] = q; phys[rows] = q; ts[rows] = t; posted[rows] = t; slot[rows] = 0
        reason[rows] = rng.choice(["COUNT_CORRECTION", "SYSTEM_ERROR", "DATA_ENTRY_FIX"], n); drift[rows] = False; locked[rows] = True
        new_case("REPEATED_ADJUSTMENTS", "PLANTED_THEFT_PATTERN", "INVESTIGATE", s, emp=emp, t0=t.min(), t1=t.max(),
                 units=-q.sum(), value=(-q * pcost[pp]).sum(),
                 desc="One manager-level employee posts many negative adjustments on a few SKUs within two weeks; physical stock really left, so counts stay clean.",
                 mov=rows, pairs=favored)

    # (d) planted theft: phantom returns (restocked on paper, nothing physically returned)
    for _ in range(n_rr):
        s = next_store(); k = int(rng.integers(0, 3)); emp = s * 8 + 2 + k
        n = int(rng.integers(5, 11)); cand = free(T_RET)
        cand = cand[rr_kind[cand - ro] == 0]
        rows = rng.choice(cand, n, replace=False)
        a0 = int(rng.integers(10, D - 40)); t = times_for_emp(rng, 2 + k, n, a0, a0 + 24)
        pp = rng.choice(store_pairs(s, 15, 6), n)
        q = rng.integers(1, 3, n)
        pair[rows] = pp; tpair[rows] = pp; qty[rows] = q; phys[rows] = 0; ts[rows] = t; posted[rows] = t; slot[rows] = 1
        reason[rows] = "NO_RECEIPT"; rr_kind[rows - ro] = 2; rr_orig[rows - ro] = -1; rr_noappr[rows - ro] = True; locked[rows] = True
        new_case("RETURN_WITHOUT_SALE_ABUSE", "PLANTED_THEFT_PATTERN", "INVESTIGATE", s, emp=emp, t0=t.min(), t1=t.max(),
                 units=q.sum(), value=(q * pcost[pp]).sum(),
                 desc="One cashier books no-receipt returns that restock stock which never came back, with no manager approval.", mov=rows, pairs=pp)

    # (e) edge case: movement refers to the wrong store (shift belongs to the true store)
    cand = free(T_SALE); cand = cand[~np.isin(cand - so, np.r_[sel, wo])]       # never touch sales that have a return
    rows = rng.choice(cand, min(n_ws, len(cand)), replace=False)
    wrong = other_pair_same_sku(tpair[rows], retail_only=True)
    ok = wrong >= 0; rows, wrong = rows[ok], wrong[ok]
    n_ws_done = len(rows)
    pair[rows] = wrong; locked[rows] = True
    for r in rows:
        new_case("MOVEMENT_WRONG_STORE", "DATA_QUALITY_EDGE_CASE", "DATA_FIX", pair_store[tpair[r]], sku=int(pair_sku[tpair[r]]),
                 t0=ts[r], t1=ts[r], units=-qty[r], value=-qty[r] * pcost[tpair[r]],
                 desc="Sale posted against a different store than the one whose shift/employee made it; both stores' books are wrong by the same quantity.", mov=[r])

    # (f) edge case: adjustment without reason; (g) adjustment by a non-authorised role
    for kind, n in (("nr", n_nrs), ("ua", n_ua)):
        rows = rng.choice(free(T_ADJ), min(n, len(free(T_ADJ))), replace=False); locked[rows] = True
        if kind == "nr":
            reason[rows] = None
            for r in rows:
                new_case("ADJUSTMENT_NO_REASON", "DATA_QUALITY_EDGE_CASE", "DATA_FIX", pair_store[pair[r]], sku=int(pair_sku[pair[r]]),
                         t0=ts[r], t1=ts[r], units=abs(qty[r]), value=abs(qty[r]) * pcost[pair[r]],
                         desc="Adjustment posted with a NULL reason code (control failure).", mov=[r])
        else:
            slot[rows] = rng.integers(1, 3, len(rows))
            for r in rows:
                new_case("UNAUTHORIZED_ADJUSTMENT", "PLANTED_THEFT_PATTERN", "INVESTIGATE", pair_store[pair[r]], sku=int(pair_sku[pair[r]]),
                         t0=ts[r], t1=ts[r], units=abs(qty[r]), value=abs(qty[r]) * pcost[pair[r]],
                         desc="Adjustment posted by a cashier / stock clerk whose role has no adjustment authority (policy breach).", mov=[r])

    # (h) edge case: transfer shows as shrinkage at BOTH ends (OUT posted late at source, IN posted early at destination)
    xo, xin_ = off["xout"][0], off["xin"][0]
    el = np.flatnonzero((~locked[xo:xo + n_x]) & (~locked[xin_:xin_ + n_x]) & (xts_out % DAY >= OPEN) & (xts_out % DAY <= 15.5 * 3600)
                        & (xq >= 6) & (xq * pcost[xs] >= 60))
    for x in rng.choice(el, min(n_xt, len(el)), replace=False):
        D_ = int(xts_out[x]); offA = int(rng.integers(3600, 7200))
        posted[xo + x] = D_ + offA + int(rng.integers(1800, 5400))      # late OUT posting
        posted[xin_ + x] = D_                                           # early IN posting (goods arrive >= 1 day later)
        locked[xo + x] = locked[xin_ + x] = True
        ci = new_case("TRANSFER_IN_TRANSIT_BOTH_ENDS", "BENIGN_EXPLANATION", "AUTO_CLOSE_BENIGN", pair_store[xs[x]], sku=int(pair_sku[xs[x]]),
                      t0=D_, t1=int(xts_in[x]), units=0, value=0, mov=[xo + x, xin_ + x], xfer=[x],
                      desc="Goods in transit: source book not yet reduced, destination book already increased -> both counts look short by the transfer quantity.")
        cA = D_ + offA; cB = D_ + int(rng.integers(7200, 18000))
        cases[ci]["cnt"] += [plan_count(xs[x], cA, cA, ci), plan_count(xd[x], cB, cB, ci)]

    # (i) edge case: count timestamp precedes a stock movement that the counter's physical count already included
    cand = free(T_SALE); cand = cand[sqty[cand - so] >= 3]
    cand = cand[(-qty[cand] * pcost[tpair[cand]] >= 40) & (ts[cand] % DAY >= OPEN + 3 * 3600) & (ts[cand] % DAY <= CLOSE - 2 * 3600)]
    cand = cand[~np.isin(cand - so, np.r_[sel, wo])]
    for r in rng.choice(cand, min(n_tp, len(cand)), replace=False):
        m = int(ts[r]); act = m + int(rng.integers(900, 3600)); rec = m - int(rng.integers(3600, 10800))
        locked[r] = True
        ci = new_case("COUNT_TIMESTAMP_PRECEDES_MOVEMENT", "DATA_QUALITY_EDGE_CASE", "DATA_FIX", pair_store[pair[r]], sku=int(pair_sku[pair[r]]),
                      t0=rec, t1=act, units=-qty[r], value=-qty[r] * pcost[pair[r]], mov=[r],
                      desc="Count recorded earlier than a sale it already reflects, so book (as of count_ts) wrongly exceeds physical.")
        cases[ci]["cnt"].append(plan_count(pair[r], act, rec, ci, entered=act + int(rng.integers(120, 1800))))

    # legit adjustments are preceded by an unrecorded physical drift of the same size
    for r in np.flatnonzero(drift & (np.arange(M) >= off["adj"][0]) & (np.arange(M) < off["adj"][1])):
        hid_add(pair[r], max(0, int(ts[r]) - int(rng.integers(1, 11)) * DAY - int(rng.integers(0, DAY))), qty[r], 1)
    hp, ht, hq, hc = (np.concatenate(x) for x in (hid_pair, hid_ts, hid_qty, hid_cause))

    # ------------------------------------------------------------------ 4. opening balances (planning pass over both timelines)
    book_min = min_running(pair, posted, qty, NP)
    phys_min = min_running(np.r_[tpair, hp], np.r_[ts, ht], np.r_[phys, hq], NP)
    base_open = rng.integers(10, 80, NP) * np.where(wh_p, 20, 1)
    opening = np.maximum(base_open, np.maximum(-book_min, -phys_min) + rng.integers(3, 30, NP)).astype(np.int64)
    P_book = PrefixSum(pair, posted, qty)
    P_phys = PrefixSum(tpair, ts, phys)
    P_h = [PrefixSum(hp[hc == c], ht[hc == c], hq[hc == c]) for c in (0, 1, 2)]

    # ------------------------------------------------------------------ 5. movement ids, shifts, employees
    order = np.argsort(posted, kind="stable")
    rank = np.empty(M, np.int64); rank[order] = np.arange(M)
    mov_id = ids("MOV-2026-", rank + 1, 8)
    shift_store = pair_store[tpair]
    pday, pst = posted // DAY, (posted % DAY >= SPLIT).astype(int)
    assert pday.max() < D and (posted % DAY >= OPEN).all() and (posted % DAY < CLOSE).all()
    shift_no = ((shift_store * D + pday) * 2 + pst) * 3 + slot
    emp_idx = shift_store * 8 + emp_local_v(pday, pst, slot)
    xf_rank = np.empty(n_x, np.int64); xf_rank[np.lexsort((np.arange(n_x), xts_out))] = np.arange(n_x)
    xfer_id = np.where(xfer >= 0, ids("XFR-2026-", xf_rank[np.maximum(xfer, 0)] + 1, 6), None)
    mv = pd.DataFrame({
        "movement_id": mov_id, "store_id": store_ids[pair_store[pair]], "sku_id": skus.sku_id.values[pair_sku[pair]],
        "movement_type": np.array(MT)[typ], "quantity_signed": qty, "reason_code": reason,
        "movement_ts": tstr(ts), "posted_ts": tstr(posted), "shift_id": ids("SHIFT-", shift_no + 1, 7),
        "employee_id": emp_ids[emp_idx], "transfer_id": xfer_id,
        "counterparty_store_id": np.where(cp >= 0, store_ids[np.maximum(cp, 0)], None),
        "promotion_id": np.where(promo >= 0, ids("PROMO-", promo + 1, 6), None), "reference_note": note})
    mv = mv.iloc[order].reset_index(drop=True)

    # ------------------------------------------------------------------ 6. cycle counts (derived from both timelines)
    n_pl = len(pc["pair"])
    n_base = cfg.n_counts - n_pl
    if n_base < 0.5 * cfg.n_counts:
        raise ValueError("n_counts too small for the planted cases at this scale")
    cw = pcost ** .5
    bp = rng.choice(NP, n_base, p=cw / cw.sum())
    bt = rng.integers(3, D, n_base) * DAY + rng.integers(OPEN, CLOSE - 3600, n_base)
    c_pair = np.r_[pc["pair"], bp].astype(np.int64)
    c_act = np.r_[pc["actual"], bt].astype(np.int64)
    c_rec = np.r_[pc["rec"], bt].astype(np.int64)
    ent = np.array(pc["entered"] + [-1] * n_base)
    c_ent = np.where(ent >= 0, ent, c_act + rng.integers(120, 1800, len(c_act)))
    c_kind = np.where(rng.random(len(c_pair)) < .75, "SCHEDULED", "SPOT_CHECK")
    c_slot = np.where(rng.random(len(c_pair)) < .6, 2, 0)
    n_cn = len(c_pair)
    noise = rng.choice([-2, -1, 0, 1, 2], n_cn, p=[.01, .05, .88, .05, .01])
    book = opening[c_pair] + P_book.q(c_pair, c_rec)
    mv_eff = P_phys.q(c_pair, c_act) - P_book.q(c_pair, c_rec)
    cu, cb, cd = (P_h[2].q(c_pair, c_act), P_h[0].q(c_pair, c_act), P_h[1].q(c_pair, c_act))
    raw = opening[c_pair] + P_phys.q(c_pair, c_act) + cu + cb + cd + noise
    counted = np.maximum(raw, 0)
    var = counted - book
    clip = counted - raw
    assert (var == mv_eff + cu + cb + cd + noise + clip).all()
    c_ord = np.argsort(c_rec, kind="stable")
    c_rank = np.empty(n_cn, np.int64); c_rank[c_ord] = np.arange(n_cn)
    cnt_id = ids("CNT-2026-", c_rank + 1, 6)
    aday, ast = c_act // DAY, (c_act % DAY >= SPLIT).astype(int)
    cs_store = pair_store[c_pair]
    c_emp = cs_store * 8 + emp_local_v(aday, ast, c_slot)
    c_shift = ids("SHIFT-", ((cs_store * D + aday) * 2 + ast) * 3 + c_slot + 1, 7)
    vval = np.round(var * pcost[c_pair], 2)
    within = (np.abs(var) <= np.maximum(2, .03 * book)) & (np.abs(vval) < 50)
    cc = pd.DataFrame({
        "count_id": cnt_id, "store_id": store_ids[cs_store], "sku_id": skus.sku_id.values[pair_sku[c_pair]], "count_type": c_kind,
        "count_ts": tstr(c_rec), "entered_ts": tstr(c_ent), "counted_by_employee_id": emp_ids[c_emp], "shift_id": c_shift,
        "book_qty": book, "counted_qty": counted, "variance_units": var, "variance_value": vval,
        "status": np.where(var == 0, "MATCHED", np.where(within, "WITHIN_TOLERANCE", "OUT_OF_TOLERANCE"))}).iloc[c_ord].reset_index(drop=True)
    causes = pd.DataFrame({
        "count_id": cnt_id, "variance_units": var, "cause_unexplained_loss": cu, "cause_background_shrink": cb,
        "cause_pre_adjustment_drift": cd, "cause_movement_timing_or_posting": mv_eff, "cause_count_noise": noise,
        "cause_clipping": clip}).iloc[c_ord].reset_index(drop=True)
    causes["variance_explained"] = (causes[[c for c in causes.columns if c.startswith("cause_")]].sum(axis=1) == causes.variance_units).astype(int)

    # every count that actually observed planted unexplained loss belongs to that case (not only the planned audit counts)
    ul_of = {int(p): i for i, c in enumerate(cases) if c["issue_type"] == "UNEXPLAINED_LOSS" for p in c["pairs"]}
    for i in np.flatnonzero(cu != 0):
        ci = ul_of.get(int(c_pair[i]))
        if ci is not None and int(i) not in cases[ci]["cnt"]:
            cases[ci]["cnt"].append(int(i))

    # ------------------------------------------------------------------ 7. store_skus with derived min_stock_level
    wk_units = np.bincount(pair[typ == T_SALE], weights=-qty[typ == T_SALE], minlength=NP) / (D / 7)
    store_skus = pd.DataFrame({
        "store_id": store_ids[pair_store], "sku_id": skus.sku_id.values[pair_sku], "opening_qty": opening,
        "opening_as_of": cfg.start_date, "min_stock_level": np.maximum(1, np.ceil(wk_units)).astype(int),
        "status": "ACTIVE", "effective_from": cfg.start_date, "effective_to": None})

    # ------------------------------------------------------------------ 8. returns
    sale_promo_disc = np.where(spromo >= 0, disc[np.maximum(spromo, 0)], 0)
    r_idx = np.arange(n_ret)
    rm = ro + r_idx                                                      # movement creation index of restock returns
    cashier = lambda i: emp_ids[emp_idx[i]]
    appr = np.where((rr_kind == 1) & ~rr_noappr, emp_ids[shift_store[rm] * 8 + emp_local_v(pday[rm], pst[rm], 0)], None)
    orig_disc = np.where(rr_orig >= 0, sale_promo_disc[np.maximum(rr_orig, 0)], 0)
    ret_a = pd.DataFrame({
        "ts": ts[rm], "store_id": store_ids[pair_store[pair[rm]]], "sku_id": skus.sku_id.values[pair_sku[pair[rm]]], "quantity": qty[rm],
        "original_sale_movement_id": np.where(rr_orig >= 0, mov_id[so + np.maximum(rr_orig, 0)], None),
        "return_movement_id": mov_id[rm], "reason_code": reason[rm],
        "refund_amount": np.round(qty[rm] * pprice[pair[rm]] * (1 - orig_disc / 100), 2),
        "processed_by_employee_id": emp_ids[emp_idx[rm]], "approved_by_employee_id": appr})
    wo_pair = sp[wo]; wo_ts = (sday[wo] + rng.integers(1, 15, n_wo)) * DAY + sec_open(n_wo)
    wo_qty = np.ones(n_wo, int); wo_day, wo_st = wo_ts // DAY, (wo_ts % DAY >= SPLIT).astype(int)
    wo_store = pair_store[wo_pair]
    ret_b = pd.DataFrame({
        "ts": wo_ts, "store_id": store_ids[wo_store], "sku_id": skus.sku_id.values[pair_sku[wo_pair]], "quantity": wo_qty,
        "original_sale_movement_id": mov_id[so + wo], "return_movement_id": None,
        "reason_code": rng.choice(["DEFECTIVE", "DAMAGED_IN_TRANSIT"], n_wo, p=[.6, .4]).astype(object),
        "refund_amount": np.round(wo_qty * pprice[wo_pair] * (1 - sale_promo_disc[wo] / 100), 2),
        "processed_by_employee_id": emp_ids[wo_store * 8 + emp_local_v(wo_day, wo_st, 1)], "approved_by_employee_id": None})
    rt = pd.concat([ret_a, ret_b], ignore_index=True).sort_values("ts", kind="stable").reset_index(drop=True)
    rt.insert(0, "return_id", ids("RET-2026-", np.arange(1, len(rt) + 1), 6))
    rt["return_ts"] = tstr(rt.pop("ts").values)
    rt["disposition"] = np.where(rt.reason_code.isin(["DEFECTIVE", "DAMAGED_IN_TRANSIT"]), "WRITE_OFF", "RESTOCK")
    rt["status"] = np.where(rt.disposition == "RESTOCK", "RESTOCKED", "WRITTEN_OFF")
    rt["customer_ref"] = ids("CUST-", rng.integers(1, 250_000, len(rt)), 6)
    rt = rt[["return_id", "store_id", "sku_id", "quantity", "original_sale_movement_id", "return_movement_id", "return_ts",
             "reason_code", "disposition", "status", "refund_amount", "customer_ref", "processed_by_employee_id",
             "approved_by_employee_id"]]

    # ------------------------------------------------------------------ 9. ground truth
    sku_ids_arr = skus.sku_id.values
    gt_rows, link_rows = [], []
    for i, c in enumerate(cases):
        gid = f"GT-{i + 1:06d}"
        emp = emp_ids[c["emp"]] if c["emp"] is not None else None
        gt_rows.append((gid, c["issue_type"], c["case_group"], store_ids[c["store"]], sku_ids_arr[c["sku"]] if c["sku"] is not None else None,
                        emp, str(tstr(c["t0"])), str(tstr(c["t1"])), c["expected"], c["units"], c["value"], c["detectable"], c["desc"]))
        link_rows += [(gid, "MOVEMENT", mov_id[r]) for r in c["mov"]]
        link_rows += [(gid, "COUNT", cnt_id[k]) for k in c["cnt"]]
        link_rows += [(gid, "TRANSFER", f"XFR-2026-{xf_rank[x] + 1:06d}") for x in c["xfer"]]
        link_rows += [(gid, "STORE_SKU", f"{store_ids[pair_store[p]]}|{sku_ids_arr[pair_sku[p]]}") for p in c["pairs"]]
    gt_cases = pd.DataFrame(gt_rows, columns=[f["name"] for f in S.GT_TABLES["ground_truth_cases"]["fields"]])
    gt_links = pd.DataFrame(link_rows, columns=["gt_id", "entity_type", "entity_id"]).drop_duplicates()

    return dict(
        tables=dict(stores=stores, skus=skus, store_skus=store_skus, employees=employees, employee_roles=employee_roles,
                    shifts=shifts, promotions=promotions, promotion_skus=promotion_skus, inventory_movements=mv,
                    cycle_counts=cc, returns=rt),
        ground_truth=dict(ground_truth_cases=gt_cases, ground_truth_links=gt_links, ground_truth_count_causes=causes),
        meta=dict(ops_ids=ops_ids, analyst_ids=analyst_ids, n_ws=n_ws_done))
