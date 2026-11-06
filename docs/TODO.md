# TODO: nodestro-examples

> Open work for this repository: release blockers, known bugs, security follow-ups, technical debt and planned improvements.
> GitHub issues are the source of truth for details; this file is the entry point and summary.
>
> **Last full review:** 2026-11-06 against `master` at `9920b74` (TODO abatement round).

## Summary

| Priority | Count |
|---|---|
| P0 Critical | 0 |
| P1 High | 0 |
| P2 Medium | 0 |
| P3 Low | 3 |
| P4 Optional | 4 |

**Release blockers:** None for this repository; every entry below is not a release blocker.

The 24 examples (format 2, six languages) build, run and pass their 49 test cases in all languages with deterministic
doubles, and the generated studio chapter `beispiele.md` is current on studio master (last regenerated with the `64e534a` pin,
studio `85a7f3d`). Key figures that a gate
decides on or that report money or days come from a tool and are checked by the runtime (live-tested for
`production-downtime` and `household-budget` with `qwen3.5:4b`). Result fields and team tags are labeled in the example's language (UX round 3). French texts use typographic apostrophes (EX-008, done 2026-11-06). Open work is
mostly the offline marker on copies (EX-003, needs nodestro-runtime RT-055), offering a memory space per copy in the
studio (EX-007), and checks that need real providers (EX-006).

## Priorities and statuses

- **P0 Critical**: data loss, security exposure, or broken core function; blocks any release.
- **P1 High**: blocks a planned release or a promised capability, or a significant risk.
- **P2 Medium**: real defect or gap with a workaround; schedule soon.
- **P3 Low**: minor defect, polish, or small debt.
- **P4 Optional**: improvement idea; not a defect.

Statuses: `Open`, `In progress` (PR linked), `Blocked` (names the blocker), `Needs decision` (owner decision pending),
`Needs external review`, `Accepted risk` (deliberately not fixed; reason stated).

## Release blockers and critical items

None known.

## Security

### EX-005 · MCP integrations of examples 3 and 8 await the MCP security acceptance

- **Priority:** P3 Low · **Status:** Blocked (MCP scope decision) · **Refs:** README "Known limitations", MCP re-review
- **What:** `supplier-comparison` and `customer-service` can bind read-only MCP tools. A working demonstration is not a
  security acceptance; the platform's MCP support is released only for a read-only server pilot.
- **Next step:** None here until the review concludes; the examples must keep working offline and never depend on MCP,
  unattended MCP or tool approvals (S-2).
- **Depends on:** nodestro-runtime RT-016 (MCP beyond the read-only pilot), nodestro-studio ST-030 (accepted MCP scope)

## Bugs and reliability

None known.

## Architecture and modularity

None known.

## Performance

None known.

## Features and enhancements

### EX-003 · Mark the offline (sample data) mode on copies

- **Priority:** P3 Low · **Status:** Needs decision · **Refs:** #39, UX audit AD-18
- **What:** Unconnected copies of examples 3 and 8 mention offline mode only at the end of the description and in the
  agent prompt; editor and run views show no label, and `Made.offline` is not stored with the workflow.
- **Next step:** Choose a visible first description line or a workflow marker field (runtime/API) set by
  `instantiate()`; the studio then shows a badge.
- **Depends on:** nodestro-studio ST-031 (badge); nodestro-runtime RT-055 (origin of an example copy, including its
  offline connections; UX round 3 examples handover B-1), exposed read-only by nodestro-api

### EX-007 · Offer a memory space of its own per copy

- **Priority:** P4 Optional · **Status:** Open · **Refs:** README "Known limitations"
- **What:** All copies of `creator-strategy` share the memory space `creator-ideas`, and all copies of `learning-plan`
  share `learning-progress`, so two learners or projects mix their memory. Since 2026-11-06 `build()` and
  `instantiate()` take `memory_space=` (checked against the runtime's space name rule); nothing passes it yet.
- **Next step:** nodestro-api's copy route and the studio's copy dialog offer an optional space name (for example
  prefilled from the copy name); needs a new examples pin.
- **Depends on:** nodestro-api (copy route), nodestro-studio (copy dialog)

## Tests and quality assurance

None known.

## Platform coverage

### EX-006 · Examples not verified with real providers

- **Priority:** P3 Low · **Status:** Open · **Refs:** README "Development", UX final review (OB-17)
- **What:** Tests prove data flow, decisions, approvals, files and checks with doubles; answer quality, the 49 test
  cases with a real model, the three orchestrated examples (10, 16, 19) with real orchestrator decisions and tier
  mapping for non-Anthropic providers are unverified. The demo MCP server was used with the desktop only.
- **Next step:** Run each copy's test series once per supported provider (costs tokens; needs owner approval) and
  record results; fix prompts or limits where cases fail.

## Documentation

None known.

## Technical debt

None known.

## Later optimizations

### EX-012 · Figures inside free-text results are not checked

- **Priority:** P4 Optional · **Status:** Needs decision · **Refs:** templates (checked figures, `source="tool"`)
- **What:** Since the downtime fix, the key figures that a gate decides on or that report money or days come from a tool and the
  runtime checks them (`source="tool"`): `production-downtime` (`downtime_share_percent`), `household-budget`
  (`monthly_surplus`, `savings_potential`), `farm-planning` (`total_margin_eur`) and `construction-delay`
  (`delay_days`); `contract-review` lists its critical clauses instead of counting them. Numbers written inside a
  free-text answer (`sales-offer`, `restaurant-menu`, `supplier-comparison`, `financial-analysis`) are still the
  model's own; their reviewers and quality checks read them, but no tool verifies them.
  Checked 2026-11-06: no condition or other automated step of these four templates decides on such a figure (they
  have no numeric result fields); only people and reviewers read them, for example the approval of the sales offer.
- **Next step:** Decide whether a figure a person approves (the offer total) should be a checked numeric field too;
  that turns the offer from free text into a structured result and needs texts in all six languages.

## Accepted risks

### EX-009 · Teams receive a text task, not the run's files

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Known limitations"
- **What:** Orchestrator teams get only a text task; the orchestrated examples summarize attached files in the step
  before the orchestrator.
- **Reason:** Runtime design of teams; the summary step is the documented workaround.

### EX-010 · Python dependencies not watched by Dependabot

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** `.github/dependabot.yml`, `.github/workflows/ci.yml`
- **What:** Dependabot updates only GitHub Actions; the Nodestro dependencies are pinned by Git commit.
- **Reason:** Pins move with the platform's pin cascade, and the blocking `pip-audit` step in CI catches known
  vulnerabilities. The original reason (private Git URLs) no longer applies now that all repositories are public
  (the comment in `dependabot.yml` says so); a pip ecosystem entry can be re-evaluated (CI no longer needs the
  `NODESTRO_READ` token).

## Cross-repository dependencies

| This repo item | Other repo | Other item | Relation |
|---|---|---|---|
| (pointer) | nodestro-studio | ST-052 (Dependabot policy: weekly groups, cooldown, manual merge; auto-merge prerequisites) | Full entry in studio |
| EX-003 | nodestro-studio | ST-031 (AD-18) | Studio shows the offline badge; this repo provides the marker. |
| EX-003 | nodestro-runtime | RT-055 (origin of an example copy) | Runtime stores the origin and offline connections; the marker builds on it. |
| EX-007 | nodestro-api, nodestro-studio | copy route and dialog | Pass `memory_space=` to `instantiate()`. |
| EX-005 | nodestro-runtime, nodestro-studio | RT-016, ST-030 (MCP scope) | Wider MCP use needs an owner decision and a new review. |
| (pointer) | nodestro-runtime | RT-056 (test double cannot finish orchestrators; UX round 3 examples handover B-3) | The three orchestrated examples cannot be run end to end with the test double; full entry in runtime. |
| — | nodestro-studio | `make example-docs` | Regenerate `beispiele.md` on every examples pin bump. |

## Maintaining this file

- Add an entry when work is identified but not done in the current PR. Use the next free ID; IDs are never reused.
- Link a GitHub issue for anything concrete enough to be picked up; keep details in the issue, not here.
- When an item is finished, delete its entry in the PR that completes it and mention the ID in the PR description.
  Git history is the record; do not keep ticked checklists.
- Accepted risks stay listed with their reason until the risk is removed or re-evaluated.
- Re-review the whole file before each release and update the "Last full review" line.
- Security issues that are not yet fixed are described only in general terms here. Report details privately
  (GitHub private vulnerability reporting), never in this file or in public issues.

## CI access to private repositories

Keep the repository secret `NODESTRO_READ`; do not delete it. CI currently installs the sibling repositories anonymously because they are public, and does not need the secret. When the repositories become private, CI authenticates again with this read-only secret, passed only in the environment of the install steps (never in a global Git configuration, a log or an image layer).
