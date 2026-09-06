# Image Tampering Detection and Localization

Planning repository for the CSE 4883 Digital Image Processing course project,
Summer 2026.

The proposed system studies whether a small, complementary set of classical
forensic cues can improve tampering detection and localization. The candidate
pool contains SIFT duplicated-content matching, JPEG compression-history
evidence, classical resampling traces, and JPEG block-grid anomalies. Validation
ablations select the smallest useful subset; the final subset is not fixed in
advance.

## Documents

- `PROJECT_HANDOFF.md` gives the approved project direction.
- `docs/requirements.md` defines the scope, deliverables, constraints, and
  acceptance criteria.
- `docs/decisions.md` records important design decisions as the team makes them.
- `docs/agents/contracts.md` defines the shared formats agents use to plan,
  dispatch, report, and verify work.

## Agent workflow

Work in this repository runs through three specialized agents defined in
`.opencode/agent/`: the architect plans and orchestrates, the coder
implements, and the critic verifies. They exchange plans, task briefs, coder
reports, and critic verdicts in the formats defined in
`docs/agents/contracts.md`.

The requirements and implementation decision are recorded in
`docs/decisions.md`. The repository contains a reproducible research prototype
and tests; generated datasets and evaluation outputs remain local artifacts
unless explicitly added.
