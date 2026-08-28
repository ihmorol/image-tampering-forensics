# Agent Sync Contracts

Binding formats for the architect, coder, and critic agents defined in
`.opencode/agent/`. Every plan, dispatch, report, and verdict uses these
formats so work stays traceable from plan to acceptance.

## State flow

```text
PLANNED -> DISPATCHED -> CODER COMPLETE -> CRITIC PASS -> ARCHITECT ACCEPTED
        -> HUMAN APPROVED (only where the plan names a human gate)
```

- A task is not done when code exists or when the coder reports COMPLETE.
  It is done at CRITIC PASS plus architect acceptance.
- Human gates (requirements approval, instructor feedback, final report)
  are never self-approved by agents.
- Every artifact references its plan id and acceptance criterion (AC) ids.

## PLAN format

The architect writes one plan per unit of work.

```text
PLAN <id>

Goal: <one measurable outcome>
Constraints: <project constraints that apply>
Ordered steps:
1. <action and expected intermediate result>
Files:
- Create: <paths or none>
- Modify: <paths or none>
Commands:
- <exact command> — expect <result>
Risks:
- <risk> — mitigation: <mitigation>
Acceptance criteria:
- AC1: <observable pass/fail condition>
Approval: <approved | awaiting decision | blocked>
```

Rules:

- Every acceptance criterion has a stable id (AC1, AC2, ...) and is
  independently decidable. "Works well" is invalid.
- Commands state expected outcomes, not just names.
- If a path, signature, or command is unknown, the plan is blocked, not
  guessed.
- Before requirements approval, plans may touch documentation only.

## TASK brief format

The architect dispatches work with the following. One primary outcome per
task; separate changes get separate task ids.

```text
TASK <id>

Role: coder | critic
Plan: <plan id>
Phase: <phase name>
Objective: <single outcome>
In scope:
- <required action>
Out of scope:
- <explicit exclusion>
Files:
- May modify: <paths or none>
- Must inspect: <paths>
Acceptance criteria: <AC ids and text>
Required commands:
- <exact command> — expect <result>
Decision status: <decisions already settled>
Report format: CODER REPORT | CRITIC VERDICT
Escalate when: <ambiguity, conflict, or failure condition>
AI-log note required: yes | no
```

Implementation briefs additionally state exact function signatures,
dtypes, shapes, and file formats.

## CODER REPORT format

```text
CODER REPORT <task id>

Status: COMPLETE | BLOCKED
Files changed:
- <path> — <change>
Acceptance evidence:
- AC1: MET | NOT MET — <evidence>
Commands:
- <command> — PASS | FAIL — <relevant verbatim output>
Deviations: none | <departure from brief and reason>
Open items: none | <question or blocker>
AI-log record: date, assistant, purpose, output used, verification
```

COMPLETE means ready for critic review, not accepted.

## CRITIC VERDICT format

```text
CRITIC VERDICT <task id>

Verdict: PASS | FAIL | BLOCKED
Acceptance criteria:
- AC1: VERIFIED | FAILED | NOT VERIFIABLE — <evidence>
Commands:
- <command> — PASS | FAIL | NOT RUN — <relevant verbatim output>
Defects:
- [P0|P1|P2] <file:line> — <problem>; violates: <criterion>;
  reproduce: <command>; expected: <result>; actual: <result>;
  affects: <AC ids>
Residual risks: none | <verified non-blocking limitation>
AI-log record: date, assistant, purpose, output used, verification
```

## Severity ladder

| Level | Meaning | Effect |
| --- | --- | --- |
| P0 | Leakage, test-set contamination, data or mask corruption, project-constraint violation | Blocks all further work |
| P1 | Unmet acceptance criterion, incorrect result, missing required evidence | Blocks PASS |
| P2 | Minor violation of the brief | Blocks PASS unless the architect records an approved waiver |

NOT VERIFIABLE requires FAIL. The critic never grants waivers.

## Escalation

- Coder BLOCKED: the coder stops before the disputed change. The architect
  resolves reversible details; requirements changes, irreversible choices,
  and constraint conflicts go to the user. The coder resumes only from a
  revised task brief, never from an informal answer.
- Critic FAIL: defects go to the architect only, never directly to the
  coder. The architect classifies each defect as fix, clarify, waive, or
  reject. A waiver that changes scope, evaluation, or claims requires user
  approval and a `docs/decisions.md` entry. Fixes are re-dispatched to the
  coder; the critic re-verifies after every fix until PASS.

## Skills policy

Agents load skills for domain work instead of improvising. Dispatchers
pass skills in `load_skills`; agents may also request a skill when a task
matches its description.

| Agent | Skill | Use it for |
| --- | --- | --- |
| architect | `architecture` | Requirements analysis, trade-off evaluation, decision records |
| architect | `domain-modeling` | Edits to `CONTEXT.md` and ADRs |
| architect | `grill-me` | Stress-testing a plan before dispatch |
| architect | `research` | Method and literature questions against primary sources |
| architect | `to-spec`, `to-tickets` | Turning an approved direction into specs and tasks |
| architect | `scientific-slides` | Proposal presentation deliverable |
| architect | `research-paper-writing` | Final report structure |
| coder | `tdd` | Test-first implementation of detectors and metrics |
| coder | `implement`, `implement-spec` | Executing an approved spec or ticket |
| coder | `diagnosing-bugs` | Root-cause work on failures |
| coder | `codebase-design` | Module boundaries and the detector interface |
| critic | `code-review` | Standards and spec review of a diff since a fixed point |
| critic | `diagnosing-bugs` | Verifying reported root causes before accepting a fix |

Skills inform how a role performs its function. They never override role
rules: the coder's expertise does not license redesign, and the critic's
does not license fixing.

## Governance ownership

- The architect owns `docs/decisions.md` and the AI-usage log
  (`docs/ai-usage-log.md`, created when project work begins).
- Coder and critic reports carry AI-log records; the architect consolidates
  them and adds its own usage.
- An AI-log entry is not "verified" without naming the human review,
  command, test, or critic evidence used.
