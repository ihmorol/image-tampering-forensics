# Project Workspace Guidance

This repository is documentation-only until the project requirements are approved. Do not add implementation code, tests, datasets, generated outputs, or dependency changes unless a later project decision explicitly authorizes them.

Keep project decisions and requirements in the documentation files under this repository. Use short, plain, professional sentences.

## Agent skills

### Agent sync contracts

The architect, coder, and critic agents in `.opencode/agent/` follow the shared plan, task, report, and verdict formats in `docs/agents/contracts.md`. Dispatches, reports, and verdicts use those formats.

Each agent is specialized: the architect for experiment design and planning, the coder for scientific Python and image processing, and the critic for metrics and research integrity. Agents load workspace skills for domain work instead of improvising; skill assignments live in `docs/agents/contracts.md`.

### Issue tracker

Issues for this repo live in GitHub Issues. External pull requests are not a triage request surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository with one root `CONTEXT.md` and decisions in `docs/decisions.md`. See `docs/agents/domain.md`.
