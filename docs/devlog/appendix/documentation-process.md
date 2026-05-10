# Documentation Process

## Goal

The documentation should preserve the project's engineering memory:

- ideas considered
- options rejected
- final decisions
- reasons for decisions
- implementation details
- verification results
- unresolved problems
- future requirements
- possible solution directions

## When To Update Docs

Update docs when any of these change:

- public CLI behavior
- data schema
- cache layout
- provider behavior
- adjustment-price semantics
- backtest execution semantics
- dependencies
- strategy interface
- result format
- future direction

## What To Update

Use this rule:

- Development session summary: update `docs/devlog/records/` and `docs/devlog/current/`.
- Durable architecture decision: add or update `docs/devlog/records/`.
- Known future work: update `docs/devlog/current/task-backlog.md`.
- Stable usage or workflow: update `docs/devlog/appendix/`.
- Very short project overview: update root `README.md`.

## ADR Template

```markdown
# ADR NNNN: Title

## Status

Proposed | Accepted | Superseded

## Context

What problem are we solving? What constraints matter?

## Decision

What did we choose?

## Reasoning

Why this choice over alternatives?

## Consequences

What gets better? What tradeoffs or risks remain?

## Follow-Up Work

What should be revisited or implemented later?
```

## Devlog Template

```markdown
# YYYY-MM-DD Short Title

## Context

What triggered this work?

## Ideas Considered

What options were discussed?

## Decisions

What did we choose and why?

## Implementation

What changed?

## Verification

What was run and what happened?

## Open Questions

What remains unresolved?

## Next Steps

What should happen next?
```

## Backlog Template

```markdown
## Area

### Problem Or Requirement

Need:

- ...

Possible direction:

- ...
```