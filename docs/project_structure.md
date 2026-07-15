# Project structure

AutoQuant keeps executable Python modules at the repository root deliberately:
the sandbox stages an explicit, reviewed set of files and runs `backtest.py`
directly. Keeping those entry points stable makes the trust boundary easy to
audit.

| Location | Purpose |
| --- | --- |
| `strategy.py` | The only strategy source changed during an experiment. |
| `backtest.py`, `data.py`, `metrics.py`, `validate.py`, `config.py` | Fixed research harness and evaluation rules. |
| `sandbox_runner.py`, `daily_controller.py` | Isolated execution entry points. |
| `ledger.py`, `record_result.py`, `memory.py`, `reviewer_summary.py` | Audit trail, snapshots, and reviewer output. |
| `experiment_manifest.py`, `universe_registry.py` | Approved experiment and universe definitions. |
| `evaluation.py`, `promote_candidate.py`, `robustness.py` | Human-only or frozen-candidate workflows. |
| `tests/` | Regression tests for the trusted harness. |
| `research_playbook.md` | Agent-facing hypothesis methodology and idea sources. |
| `docs/` | Input policy and implementation history. |
| `manifests/` | Human-approved experiment manifests. |
| `data/`, `runs/` | Local inputs and generated artifacts; both are ignored by Git. |

## Common commands

```bash
make test
make image
make preflight MANIFEST=manifests/<manifest>.json
make run MANIFEST=manifests/<manifest>.json
```

Run `make run` only after a human has approved the manifest's specific
hypothesis. It invokes the controller from the primary checkout.
