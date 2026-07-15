# AutoQuant Research Playbook

Use this playbook to turn an economic observation into one bounded, causal,
auditable experiment. It is a source of hypotheses, not a signal to optimize
every available rule or parameter.

The initial QQQ dataset is a sample input and a convenient single-asset test
case. A result on QQQ alone is not evidence that a strategy is generally
useful. State the intended universe before each experiment: for example, broad
equity ETFs, international equities, duration-sensitive assets, commodities,
or a specified multi-asset portfolio once the strategy interface supports it.

## Research Rules

1. Start with a mechanism, not a metric.
   Explain why the effect might exist after trading costs: behavioural delay,
   risk transfer, liquidity provision, institutional rebalancing, or a
   persistent exposure to an identified risk.
2. Make one focused change per attempt.
   Do not combine a new signal, a new filter, and several parameter changes in
   the same experiment.
3. Define the expected failure mode before running the backtest.
   A rule that should work only in persistent trends, for example, should be
   expected to struggle in range-bound markets.
4. Use only information available at the signal timestamp. Respect the
   harness's next-bar execution model.
5. Treat all visible data as research data. Do not use the locked holdout to
   generate, select, or refine an idea.
6. Do not use the robustness panel to choose parameters. Evaluate only a
   frozen candidate on it.
7. Google News may inform qualitative hypothesis discovery. Record consulted
   articles and translate them into an economic mechanism; never treat a
   headline or article timestamp as a causal input without an approved,
   versioned news dataset.
8. Use SSRN/NBER for finance and asset-pricing ideas, FRED/ALFRED for macro
   hypotheses, and SEC EDGAR for fundamental-data ideas. A source of ideas is
   not automatically an approved strategy input.

## Hypothesis Template

Record the following before editing `strategy.py`:

```text
Family:
Intended universe:
Economic mechanism:
Signal and causal inputs:
Single change from the current champion:
Expected benefit:
Expected failure regime:
Cost/turnover expectation:
Pre-committed rejection condition:
```

## Complexity card

Every new manifest must include a `complexity_budget` with: `new_features`,
`new_free_parameters`, `new_branches`, `parameter_values_considered`,
`parameter_value_sources`, `expected_trade_count`, and
`effective_degrees_of_freedom`. Declare each value before implementation. Treat
effective degrees of freedom as a conservative audit count of independently
chosen features, tunable values, and decision branches—not a formal statistical
estimate. Historical manifests without the card are legacy records only.

Within a predeclared material-performance equivalence band, prefer the candidate
with fewer effective degrees of freedom, fewer branches/features, lower
turnover, and the clearer economic mechanism.

Example:

```text
Family: medium-term momentum with volatility filter
Intended universe: liquid broad equity ETFs
Economic mechanism: gradual information diffusion and investor underreaction
Signal and causal inputs: positive trailing 126-session total return; use only
  close data known at the signal date
Single change: remain in cash when trailing 20-session realized volatility is
  above a pre-specified threshold
Expected benefit: avoid some unstable momentum episodes and reduce drawdown
Expected failure regime: sharp V-shaped recoveries and quiet mean-reverting markets
Cost/turnover expectation: modest increase from regime transitions
Pre-committed rejection condition: validation Sharpe does not improve by 0.10,
  or viability disappears at 10 bps costs
```

## Idea Families

Choose a family because its mechanism fits the intended universe. These are
starting points, not a license to run a large parameter sweep.

### Machine learning and neural models

ML is a modelling approach, not an economic mechanism. Use it only when a
pre-specified causal feature set and mechanism justify the model. For each
approved ML experiment, state the model class, all features, training window,
refit schedule, seed, parameter budget, compute requirement, and a simple
non-ML benchmark. Fit each prediction using only data available at that signal
time. Use only compute approved for the run; a GPU-enabled runner other than
the approved Colab workflow, new package, external dataset, or parameter search
requires separate human approval before implementation.

For an approved GPU training run, use the Google Colab CLI's ephemeral job
mode. Treat the remote runtime as untrusted external compute: upload only the
minimal reviewed code and approved development/validation inputs, avoid Drive
and GCP mounts, and stop the session after the job. A Colab result is not a
final AutoQuant result until the local controller evaluates and records the
identical strategy and fixed model artifact.

### Trend and momentum

Possible mechanisms: investor underreaction, slow-moving institutional flows,
and persistent macro/risk regimes. Usually more plausible for liquid index,
country, sector, futures, and asset-class instruments over medium horizons.

Research variations:

- Compare fixed lookbacks chosen *before* the batch, such as 3, 6, and 12
  months.
- Require agreement between price trend and trailing return.
- Scale exposure down, rather than switch fully off, when realized volatility
  rises.
- Test entry/exit hysteresis to reduce whipsaw turnover.

Expected weakness: sideways markets, abrupt reversals, and crowded exits.

### Short-horizon mean reversion

Possible mechanisms: temporary liquidity imbalance, forced flows, and
overreaction. This is more plausible in deep, liquid instruments and requires
especially conservative cost assumptions.

Research variations:

- Define an abnormal move relative to trailing volatility, not a fixed percent.
- Test a short, pre-specified holding horizon.
- Condition the signal on a broad trend or stress regime rather than assuming
  it works everywhere.

Expected weakness: persistent selloffs, gaps, and transaction costs.

### Volatility and risk management

Possible mechanisms: volatility clustering and the convexity of drawdown
avoidance. Risk management can improve portfolio utility without creating
positive alpha by itself; report both absolute and benchmark-relative results.

Research variations:

- Volatility-target an otherwise fixed, economically motivated signal.
- Compare a small set of pre-declared volatility windows.
- Add a maximum-exposure cap during unusually volatile regimes.

Expected weakness: volatility can fall after a selloff, causing delayed
re-entry; scaling can also increase turnover and miss rebounds.

### Regime-conditioned signals

Possible mechanisms: trend, reversion, and volatility premia vary across
macro, volatility, and correlation regimes. A regime definition must be
observable and simple enough to avoid becoming a hidden optimizer.

Research variations:

- Condition a base signal on its own trailing volatility.
- For a future multi-asset interface, use a pre-specified market breadth or
  cross-asset risk indicator with clear data provenance.
- Test whether a signal should reduce exposure rather than reverse direction.

Expected weakness: regime labels are noisy; extra filters can overfit and
reduce sample size.

### Cross-sectional and relative-value signals

These require a genuine multi-asset strategy contract and synchronized,
survivorship-aware universe data. Do not simulate them by applying independent
single-asset rules and informally comparing results.

Candidate mechanisms include relative momentum, valuation dispersion, carry,
and sector/country rotation. Define membership, rebalance schedule, ranking,
weighting, turnover controls, and delisting treatment before testing.

### Defensive and diversifying allocations

For a future portfolio implementation, test whether combining assets with
different economic drivers improves drawdown and risk-adjusted return. Examples
include equity, duration, inflation-sensitive, and commodity exposures. This is
portfolio construction, not proof that each component has alpha.

## Authorized execution protocol

Read experiment memory, this playbook, and `policy.toml` before an authorized
run. After explicit approval, create a manifest, test one focused `strategy.py`
change, and invoke `daily_controller.py` from the primary checkout. The
controller is the sole selection path: it reserves selection budget, records
immutable artifacts, and writes the report.

Classify outcomes as `invalid` (implementation, causality, or data-integrity
failure), `rejected` (valid experiment failed precommitted criteria),
`inconclusive` (insufficient evidence), `candidate` (passes research criteria),
or `promoted` (independent evaluation and operational review pass). Historical
statuses remain legacy records.

## Experiment Design

Use the smallest credible experiment:

1. Search the experiment memory for related hypotheses and failures.
2. Select one family and complete the hypothesis template.
3. Present the complete hypothesis and rejection condition to the human, and
   wait for explicit approval before creating the experiment manifest or
   performing any backtest. A request for general research is not approval.
4. Pre-declare a small parameter set or one parameter change. Do not expand it
   after seeing results within the same batch.
5. Implement the causal rule in `strategy.py` and run the fixed test/backtest
   workflow.
6. Inspect development, visible research-period stability, costs, exposure,
   benchmark-relative performance, and obvious failure regimes.
7. Record the result—including a rejection—and revert unsuccessful changes.
   A rejection applies to its declared universe, mechanism, implementation,
   parameterization, and failure regime. Record whether it is an implementation
   failure, a specific-hypothesis failure, or stronger repeated negative evidence;
   do not generalize it to an entire family without that evidence.
8. Freeze the source and parameters before the robustness-panel evaluation.

## What Not To Do

- Do not search many lookbacks, thresholds, and filters until one happens to
  pass the acceptance thresholds.
- Do not select on a single annual period, one extreme crisis, or total return
  alone.
- Do not infer tradability from adjusted-close backtests.
- Do not claim a strategy transfers between asset classes merely because it did
  not fail on a small stress panel.
- Do not treat a failed hypothesis as useless: record its intended universe and
  failure regime so it informs later research.

## When to Expand the Dataset or Interface

Request human approval before adding data or changing the strategy contract.
Expansion is justified when the hypothesis cannot be tested honestly with the
current single-asset daily OHLCV interface—for example, cross-sectional
momentum, breadth, carry, valuation, intraday liquidity provision, or portfolio
allocation. Specify the economic need, universe construction, data source,
history availability, corporate-action/delisting treatment, and revised cost
model in the approval request.
