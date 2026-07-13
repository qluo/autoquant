# Approved market-input policy

Routine research uses only the committed local CSV inputs and their provenance
sidecars. The daily controller verifies that each required CSV and sidecar is
present before starting an experiment; it never downloads or refreshes data.

Refreshing or adding an input requires human approval before a research batch:

- state the source, ticker/universe, date range, adjustment convention, and
  calendar/missing-session policy;
- save the CSV and provenance sidecar together, including retrieval timestamp
  and SHA-256 hash;
- review corporate-action and lookahead implications; and
- start a new batch rather than treating a data refresh as evidence for an
  existing candidate.

Cross-sectional or portfolio research additionally requires approved
synchronized membership, benchmark, cost, and portfolio-construction policies.
