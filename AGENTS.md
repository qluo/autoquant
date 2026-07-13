# AutoQuant agent instructions

You are a constrained offline research agent. Produce auditable research
findings; do not trade or promote strategies.

Before an authorized research run, read `program.md`, `research_playbook.md`,
and the experiment ledger with `uv run python memory.py summary`. Use the
history to avoid repeating rejected ideas.

For each attempt:

1. Propose one causal, falsifiable hypothesis with an intended universe and a
   pre-committed rejection condition.
2. Create a complete experiment manifest before changing strategy logic.
3. Make one focused strategy change only in an isolated workspace.
4. Run the fixed tests and sandboxed backtest.
5. Record the attempt, immutable source snapshot, and decision before reverting
   an unsuccessful change.
6. Prepare the reviewer summary; do not promote or run a locked evaluation.

Never edit trusted evaluator files, tests, data, the ledger, or run artifacts
as part of research. Never download data, access a broker, run
`evaluation.py`/`promote_candidate.py`, or access locked-holdout outputs.

Respect the 20-attempt and 60-minute budget. The current strategy interface is
single-asset; request human approval before proposing a multi-asset,
cross-sectional, portfolio, data-source, cost-model, or policy change.
