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
3. Make one focused change only in `strategy.py`. After explicit approval, the
   controller may copy that reviewed source—including an uncommitted ML
   implementation—into its isolated workspace with `--strategy-source
   strategy.py`. Do not use the robustness panel for research or tuning.
4. Use only the approved controller and recorder to create ledger events,
   snapshots, results, and reviewer reports; do not edit those artifacts
   directly. The controller creates its own temporary worktree; invoke it only
   from the primary checkout, never from an outer linked or temporary worktree.
   `runs/sandbox/latest_result.json` is replaceable sandbox output: rerun the
   approved sandbox runner if it is stale or unwritable; never manually use
   `rm`, `chmod`, or `chown` on it.
5. Never alter trusted evaluator files, tests, data, policy, cost assumptions,
   or evaluation windows. Never access brokers, locked-holdout outputs,
   `evaluation.py`, or `promote_candidate.py`.
6. Respect the 20-attempt and 60-minute budget. The final report must compare
   the candidate with the fixed buy-and-hold baseline.
7. ML models are allowed only when their model class, causal features, fixed
   parameter budget, and rejection condition are stated in the approved
   hypothesis. They must be deterministic and train only on the information
   available at each signal time. Use only compute resources approved for the
   run; a new dependency, GPU-enabled runner other than the approved Colab
   workflow below, external dataset, or
   hyperparameter search requires separate human approval before implementation.
8. Approved deep-learning training may use the installed Google Colab CLI and
   `colab-operator` skill with one ephemeral GPU job. Send only the reviewed
   strategy, minimal job code, and approved development/validation inputs; do
   not send `.git`, `runs/`, ledger data, holdout inputs, credentials, or mount
   Drive/GCP services. Stop the session when the job ends. Colab output is
   exploratory compute only: the local controller remains the only way to
   create an attempt record and final report.
9. Treat visible selection evidence as finite. `qqq_selection_v1` permits at
   most 50 effective hypothesis fingerprints and 3 advanced candidates. The
   controller reserves the fingerprint before selection execution; failed runs
   still consume budget. Do not inspect selection metrics through direct sandbox
   runs, manual tests, or related parameter variants. When the budget is
   exhausted, the selection dataset is retired until a human approves a new,
   pinned dataset version and period.
10. Every new hypothesis must carry the structured complexity card in
    `research_playbook.md`. Do not hide multiple features, branches, or tuning
    choices inside one “focused” change. When evidence is materially equivalent,
    prefer the simpler candidate.
11. Neural models are prohibited by default for the current single-asset daily
    dataset. An exception needs explicit human approval with a sample-size and
    complexity justification. Any approved ML run must use walk-forward
    retraining, prefix-only scaling/imputation, declared label purge/embargo,
    fixed multiple seeds, missing-data behavior, feature timestamps, and a
    linear/logistic comparator. Do not select the best seed or model variant.
12. A locked-holdout version permits one full disclosure only. After any lookup,
    pass or fail, treat it as retired for final claims and do not use its result
    to refine another candidate.
    Predeclare the complete holdout report before opening it; compare the frozen
    champion and fixed baselines, not buy-and-hold alone, and do not run
    follow-up diagnostics after disclosure.
