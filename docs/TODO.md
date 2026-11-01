# TODO: nodestro-examples

> Open work for this repository: release blockers, known bugs, security follow-ups, technical debt and planned improvements.
> GitHub issues are the source of truth for details; this file is the entry point and summary.
>
> **Last full review:** 2026-11-01 against `master` at `ebe899a`.

## Summary

| Priority | Count |
|---|---|
| P0 Critical | 0 |
| P1 High | 0 |
| P2 Medium | 0 |
| P3 Low | 7 |
| P4 Optional | 4 |

**Release blockers:** None for this repository.

The 24 examples (format 2, six languages) build, run and pass their 49 test cases in all languages with deterministic
doubles, and the generated studio chapter `beispiele.md` is current at studio `8e18cae`. Open work is mostly
localization polish from the UX initiative, one stale documentation note, and checks that need real providers.

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

- **Priority:** P3 Low · **Status:** Needs external review · **Refs:** README "Known limitations", MCP re-review
- **What:** `supplier-comparison` and `customer-service` can bind read-only MCP tools. A working demonstration is not a
  security acceptance; the platform's MCP support is released only for a read-only server pilot.
- **Next step:** None here until the review concludes; the examples must keep working offline and never depend on MCP,
  unattended MCP or tool approvals (S-2).
- **Depends on:** nodestro-runtime / nodestro-api MCP review

## Bugs and reliability

### EX-001 · Team capability tags are English in every language

- **Priority:** P3 Low · **Status:** Open · **Refs:** #38, UX audit ED-17
- **What:** The tags of the ten parts are in the language-neutral `templates/parts/*.json`, so the editor palette and
  the orchestrator prompt show English tags in all languages. The library does not use `select`, so translating them
  does not change team matching.
- **Next step:** Move the tags into `texts/<language>/<part>.json` for all six languages, with a check and a test.

### EX-002 · Long field descriptions make structured results show English field ids

- **Priority:** P3 Low · **Status:** Needs decision · **Refs:** UX audit ED-17, six-language journeys report
- **What:** The studio labels a structured result field by its description only up to 60 characters; otherwise it
  humanizes the English field id (`key_terms` → "Key terms"). 10 to 17 of the 76 field descriptions per language are
  longer, partly because they also instruct the model (e.g. `contract-review` `critical_count`).
- **Next step:** Decide between a separate short label per field (needs a `label` on the runtime's `OutputField`) and
  shortening descriptions where the model does not need the detail; then add a test for the chosen limit.
- **Depends on:** nodestro-runtime (`OutputField`), nodestro-studio (`fieldLabel()`, palette team hint)

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
- **Depends on:** nodestro-studio (badge); nodestro-runtime and nodestro-api if a marker field is chosen

### EX-007 · Separate memory spaces per copy

- **Priority:** P4 Optional · **Status:** Open · **Refs:** README "Known limitations"
- **What:** All copies of `creator-strategy` share the memory space `creator-ideas`, and all copies of `learning-plan`
  share `learning-progress`, so two learners or projects mix their memory.
- **Next step:** Consider an optional space suffix chosen when copying (e.g. from the copy name).

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

### EX-004 · Stale "Known limitation" on approval comments

- **Priority:** P3 Low · **Status:** Open · **Refs:** README "Known limitations", `tests/test_cases.py` (approval
  without comment), runtime CHANGELOG (platform integration fixes)
- **What:** The README says an approval comment becomes an extra result of the result node. The runtime no longer
  passes approval comments to result nodes or decisions, so the note and the comment-free workaround in the test are
  outdated (checked: all 49 cases pass in six languages when approved with a comment).
- **Next step:** Approve with a comment in `test_cases.py` to prove the fix, then remove the README note.

## Technical debt

### EX-008 · Typographic apostrophes in fr, it and en texts

- **Priority:** P4 Optional · **Status:** Open · **Refs:** identified in this inventory
- **What:** The example texts use straight apostrophes only (about 1,570 in fr, 730 in it, 120 in en), while the
  studio locales mostly use typographic ones, so gallery and guides mix both styles.
- **Next step:** Follow the studio's typography decision and convert in one pass, leaving code, placeholders and
  file names unchanged; add a test that keeps the style.
- **Depends on:** nodestro-studio (fr apostrophe cleanup)

### EX-011 · CI requires the `NODESTRO_READ` token although the dependencies are public

- **Priority:** P3 Low · **Status:** Open · **Refs:** #40, backend audit D-08 residual
- **What:** The CI install steps exit when the `NODESTRO_READ` secret is missing and still call the components
  private. All Nodestro repositories and orkexa are public now, so runs without secrets (Dependabot, forks) fail early.
- **Next step:** Install the git dependencies anonymously, make the token optional or remove it, fix the comments.
- **Depends on:** none; the same change is tracked in nodestro-api #50, nodestro-sdk #47, nodestro-server #25,
  nodestro-desktop #17 and nodestro-studio #85.

## Later optimizations

None known.

## Accepted risks

### EX-009 · Teams receive a text task, not the run's files

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Known limitations"
- **What:** Orchestrator teams get only a text task; the orchestrated examples summarize attached files in the step
  before the orchestrator.
- **Reason:** Runtime design of teams; the summary step is the documented workaround.

### EX-010 · Python dependencies not watched by Dependabot

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** `.github/dependabot.yml`, `.github/workflows/ci.yml`
- **What:** Dependabot updates only GitHub Actions; the private Nodestro dependencies are pinned by Git commit.
- **Reason:** Dependabot cannot read the private Git URLs; pins move with the platform's pin cascade, and the blocking
  `pip-audit` step in CI catches known vulnerabilities.

## Cross-repository dependencies

| This repo item | Other repo | Other item | Relation |
|---|---|---|---|
| EX-002 | nodestro-runtime | pointer in its cross-repo table | A per-field `label` on `OutputField` would let examples keep long descriptions. |
| EX-002 | nodestro-studio | ST-032 (ED-17) | `fieldLabel()` and the palette team hint show field ids. |
| EX-003 | nodestro-studio | ST-031 (AD-18) | Studio shows the offline badge; this repo provides the marker. |
| EX-005 | nodestro-runtime, nodestro-api | MCP review | Acceptance of MCP support. |
| EX-008 | nodestro-studio | ST-026 (fr apostrophes) | Same typography decision. |
| — | nodestro-studio | `make example-docs` | Regenerate `beispiele.md` on every examples pin bump. |
| EX-011 | all component repositories | `NODESTRO_READ` CI change (api #50, sdk #47, runtime #75, server #25, desktop #17, studio #85) | Same change everywhere |

## Maintaining this file

- Add an entry when work is identified but not done in the current PR. Use the next free ID; IDs are never reused.
- Link a GitHub issue for anything concrete enough to be picked up; keep details in the issue, not here.
- When an item is finished, delete its entry in the PR that completes it and mention the ID in the PR description.
  Git history is the record; do not keep ticked checklists.
- Accepted risks stay listed with their reason until the risk is removed or re-evaluated.
- Re-review the whole file before each release and update the "Last full review" line.
- Security issues that are not yet fixed are described only in general terms here. Report details privately
  (GitHub private vulnerability reporting), never in this file or in public issues.
