# Prompt history

Required by the submission guidelines ("include all prompts submitted to every AI tool"). Tool: **Claude (Anthropic) in the claude.ai chat**. Responses are optional per the FAQ; they are summarised below.
**Add any other prompts you send (other tools, follow-ups) to this file.**

## Prompt 1
> *(attached: the YottaFlex.ai "72 Hours Code Challenge" problem statement text, the "Candidate Project FAQ" image and the "Candidate Project Submission Guidelines" image)*
> "Do this assessment and say what they given assessment and what is our approach and complete the assessment"

Outcome: analysis of the brief, design of the solution, and implementation of the generator, detector, validator, evaluator, tests and docs.

## Prompt 2
> "complete this assessment say how to run in vs code and give me commands to files and folders to run this assessment"

Outcome: run instructions, VS Code configuration (`.vscode/`), `run.py` launcher.

## Prompt 3
> "give me complete assesment task zip file, it shoule be proper for submisson ready and give me commands to run this in vs code,.first i will download zip file which u give and then i will open the entier folder and give me commands to run this assessemnent"

Outcome: this packaged repository (`inventory-shrinkage-detection.zip`), final full-scale run, reproducibility report, README.

## Iterations performed with the AI (evidence of validation)
1. First run of starter profile: 200/203 checks passed → fixed alert lifecycle (alert escalated before it existed), a too-broad reconciliation check, and alert texts that did not cite record IDs.
2. First full run: 203/203 checks passed, but INVESTIGATE precision 76 % → diagnosed (a) warehouses legitimately write off many items daily so the damage-spike rule needed a per-store baseline and a documented-value share, (b) routine counts that observed planted loss were not linked in ground truth. Both fixed.
