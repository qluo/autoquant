from __future__ import annotations

import datetime as dt


DEVELOPMENT_END = dt.date(2017, 12, 31)
VALIDATION_END = dt.date(2021, 12, 31)
HOLDOUT_START = dt.date(2022, 1, 1)
VALIDATION_FOLDS = (
    (dt.date(2014, 1, 1), dt.date(2015, 12, 31)),
    (dt.date(2016, 1, 1), dt.date(2017, 12, 31)),
    (dt.date(2018, 1, 1), dt.date(2019, 12, 31)),
    (dt.date(2020, 1, 1), dt.date(2021, 12, 31)),
)

DEFAULT_TRANSACTION_COST_BPS = 2.0
PROMOTION_COST_SCENARIOS_BPS = (2.0, 5.0, 10.0)

# The autonomous loop must stop when either limit is reached.
MAX_EXPERIMENT_ATTEMPTS = 20
MAX_EXPERIMENT_MINUTES = 60
