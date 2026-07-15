from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path


POLICY = tomllib.loads((Path(__file__).with_name("policy.toml")).read_text())


DEVELOPMENT_END = dt.date.fromisoformat(POLICY["windows"]["development_end"])
VALIDATION_END = dt.date.fromisoformat(POLICY["windows"]["selection_end"])
HOLDOUT_START = dt.date.fromisoformat(POLICY["windows"]["holdout_start"])
HOLDOUT_ID = POLICY["windows"]["holdout_id"]
MAX_HOLDOUT_LOOKUPS = POLICY["holdout"]["max_lookups"]
MAX_HOLDOUT_LOOKUPS_PER_BATCH = POLICY["holdout"]["max_lookups_per_batch"]
HOLDOUT_MIN_EXCESS_ANNUAL_RETURN = 0.0
HOLDOUT_MAX_DRAWDOWN_WORSENING = 0.02
VALIDATION_FOLDS = (
    (dt.date(2014, 1, 1), dt.date(2015, 12, 31)),
    (dt.date(2016, 1, 1), dt.date(2017, 12, 31)),
    (dt.date(2018, 1, 1), dt.date(2019, 12, 31)),
    (dt.date(2020, 1, 1), dt.date(2021, 12, 31)),
)

DEFAULT_TRANSACTION_COST_BPS = 2.0
PROMOTION_COST_SCENARIOS_BPS = (2.0, 5.0, 10.0)

# The autonomous loop must stop when either limit is reached.
MAX_EXPERIMENT_ATTEMPTS = POLICY["research"]["max_experiment_attempts"]
MAX_EXPERIMENT_MINUTES = POLICY["research"]["max_experiment_minutes"]

# Visible selection evidence is a finite resource, not a reusable validation set.
SELECTION_DATASET_ID = POLICY["research"]["selection_dataset_id"]
MAX_EFFECTIVE_HYPOTHESES = POLICY["research"]["max_effective_hypotheses"]
MAX_CANDIDATES_ADVANCED = POLICY["research"]["max_candidates_advanced"]

ROBUSTNESS_CORE_TICKERS = ("SPY", "IWM", "EFA", "EEM")
ROBUSTNESS_STRESS_TICKERS = ("TLT", "GLD")
