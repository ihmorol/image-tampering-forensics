# Issue tracker: GitHub

Issues and project requirements for this repo live in GitHub Issues. Use the `gh` CLI for issue operations.

## Conventions

- Create an issue with `gh issue create --title "..." --body "..."`.
- Read an issue with `gh issue view <number> --comments`.
- List issues with `gh issue list --state open` and filter by labels when needed.
- Comment with `gh issue comment <number> --body "..."`.
- Add or remove labels with `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- Close an issue with `gh issue close <number> --comment "..."`.

The repository remote is the source of truth for the GitHub owner and repository name.

## Pull requests as a request surface

PRs as a request surface: no. External pull requests are not included in normal issue triage.

## Publishing and fetching

When a skill says to publish to the issue tracker, create a GitHub issue. When it says to fetch a ticket, run `gh issue view <number> --comments`.
