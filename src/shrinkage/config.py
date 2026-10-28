"""Scale parameters. Starter and full datasets use the SAME generator; only these numbers differ."""
from dataclasses import dataclass, asdict

PROFILES = {
    "starter": dict(n_stores=10, n_skus=500, n_movements=20_000, n_counts=500, skus_per_store=200),
    "full": dict(n_stores=100, n_skus=5_000, n_movements=1_000_000, n_counts=20_000, skus_per_store=1_000),
}

OPEN, SPLIT, CLOSE, DAY = 6 * 3600, 14 * 3600, 22 * 3600, 86_400   # store hours 06:00-22:00, 2 shifts of 8h


@dataclass(frozen=True)
class Config:
    seed: int = 20261022
    n_stores: int = 100
    n_skus: int = 5_000
    n_movements: int = 1_000_000
    n_counts: int = 20_000
    skus_per_store: int = 1_000          # assortment size per store (warehouses carry 2x)
    start_date: str = "2026-01-01"       # opening balances are as-of this date
    days: int = 181                      # activity window: 2026-01-01 .. 2026-06-30
    as_of_days: int = 212                # alerts / investigations are evaluated as-of 2026-08-01
    year: int = 2026

    @property
    def as_of_sec(self) -> int:
        return self.as_of_days * DAY

    def to_dict(self):
        return asdict(self)


def make_config(profile="full", **overrides) -> Config:
    base = dict(PROFILES[profile])
    base.update({k: v for k, v in overrides.items() if v is not None})
    return Config(**base)
