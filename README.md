# Image Tampering Detection and Localization

Planning repository for the CSE 4883 Digital Image Processing course project,
Summer 2026.

The proposed system will detect and localize image tampering by combining three
classical forensic cues: SIFT copy-move matching, JPEG ghost analysis, and JPEG
block-grid inconsistency analysis. No implementation has started yet.

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

This repository is intentionally documentation-only until the team approves the
requirements and implementation plan.
