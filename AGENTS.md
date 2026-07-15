# AutoQuant agent guardrails

Read `program.md`, `research_playbook.md`, and experiment memory before any
authorized run. `program.md` is the canonical execution protocol;
`research_playbook.md` is the canonical source for methodology and idea sources.

Non-negotiable rules:

1. Propose one bounded, falsifiable hypothesis and obtain explicit human
   approval before creating a manifest, changing strategy logic, or running an
   experiment. A general request to research is not approval of a hypothesis.
2. Select `universe_id` only from `universe_registry.py`. If an idea requires an
   unregistered universe, dataset, or policy change, stop and request approval
   before creating a manifest, downloading data, or running an experiment.
3. Make one focused change only in an isolated workspace. Do not use the
   robustness panel for research or tuning.
4. Use only the approved controller and recorder to create ledger events,
   snapshots, results, and reviewer reports; do not edit those artifacts
   directly.
5. Never alter trusted evaluator files, tests, data, policy, cost assumptions,
   or evaluation windows. Never access brokers, locked-holdout outputs,
   `evaluation.py`, or `promote_candidate.py`.
6. Respect the 20-attempt and 60-minute budget. The final report must compare
   the candidate with the fixed buy-and-hold baseline.
