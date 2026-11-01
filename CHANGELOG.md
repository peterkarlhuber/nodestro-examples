# Changelog

## Unreleased

### Runtime pin: Amazon Bedrock (branch only, 2026-11-01)

- Pin of `nodestro-runtime` at `ac96c6f` (before: `d141b8f`) on the Bedrock branch, so the dependent nodestro-api
  branch resolves one runtime (the runtime adds the `bedrock` provider; nothing here changes).

### Runtime pin: PostgreSQL read performance (2026-11-01)

- Pin of `nodestro-runtime` at `d141b8f` (before: `6eacec1`): the PostgreSQL store checks pooled connections only
  after they sat idle, retries reads on a lost connection, and its find indexes are partial (migration 0006).

### Runtime pin: backend audit fixes (2026-11-01)

- Pin of `nodestro-runtime` at `6eacec1` (before: `58cec5c`): fixes from the internal backend audit (bounded sandbox
  output, run integrity across processes, PostgreSQL connection pool, resume side-effect journal, provider failure
  codes; see the runtime CHANGELOG).

### Template format 2 and the modernized examples (2026-11-01)

- `FORMAT_VERSION = 2`, package version 0.3.0. New, optional template features, validated on load: model tiers
  (`fast`, `standard`, `strong`) with `model_choice()` instead of fixed models; orchestrator nodes over parts
  (teams with capabilities, limits, staffing and parameters); knowledge files of the template (stored when copied,
  searched with citations); persistent memory; optional read-only MCP integrations with a labelled offline mode;
  loops; output contracts; sanitized result files; budget and limits. Guides gain `control` (who decides what) and
  `why` (why this architecture) in all six languages.
- `instantiate()` creates everything a copy needs through a host (knowledge files once, parts in dependency order,
  every reference pinned); `connect()` binds an integration only to approved read-only tools and raises
  `IntegrationProblem` otherwise. The API models gain teams, integrations, knowledge, budget and the orchestrator
  agent kind; the pattern `adaptive`.
- Examples 10 (research), 16 (business idea) and 19 (construction delay) are orchestrated: a coordinator chooses
  among four or five expert teams, runs independent teams in parallel, sets team parameters (research) or staffs a
  team (construction; the claims team stops for a site manager's sign-off).
- Example 2 searches an archive of past 8D reports, 12 checks contracts against a company playbook, 24 answers from
  stored municipal rules with citations, an approval with revision and a sanitized reply file.
- Examples 3 and 8 can read an ERP or shop system through MCP (`erp`, `shop`); without a connection they use an
  exported file (new sample files `history` and `orders`). `python -m nodestro_examples.demo_mcp` is a local
  read-only demo server with the same synthetic data.
- Example 6 uses one structured brief instead of two planners, 7 sends a rejected offer back for revision (the
  writer recalculates with the calculator), 9 ends with a hiring manager's approval, 13 remembers the learner's
  progress, 23 sends a campaign the credibility review rejects back to the writer (at most twice).
- New test files `test_format2.py` and `test_demo_mcp.py`; 49 test cases (before 45). The quality judge now follows
  the workspace's provider (the former Anthropic-only judge limitation is gone).
- `docs.py` documents teams, integrations, knowledge files and the two new guide sections.

### Runtime pin: MCP re-review fixes R-1, R-2 (2026-11-01)

- Pin of `nodestro-runtime` at `58cec5c` (before: `f71086a`): a per-call approval also covers the tool's
  classification (a reclassification while a call waits makes the approval stale), and the tool name `memory` is
  reserved for the agent's memory tool.

### Runtime pin: MCP security fixes (2026-11-01)

- Pin of `nodestro-runtime` at `f71086a` (before: `c86781b`): fixes from the independent MCP review (per-call
  approvals hold in agent tests and the tool panel, no credentials in server addresses, response size limit) and the
  offline worker fix F5. No change in this package.

### Runtime pin: runs paused at a tool approval (2026-11-01)

- Pin of `nodestro-runtime` at `c86781b` (before: `6ac4ae3`): with the new switch
  `NODESTRO_TOOL_APPROVAL_CHECKPOINTS` (default off) a tool call that waits for a person pauses the run and
  continues it after the decision without asking the model again (AO M6b). No change in this package.

### Runtime pin: security fix for stale tools in server workers (2026-11-01)

- Pin of `nodestro-runtime` at `6ac4ae3` (before: `081705d`): every process sees tool changes and deletions made by
  another process, and a tool an agent holds refuses to run once its version is no longer the current approved one
  (S-2 pilot finding F1). No change in this package.

### Runtime pin: dynamic teams and approvals inside teams (2026-11-01)

- Pin of `nodestro-runtime` at `081705d` (before: `1bc3924`): orchestrators wait for approvals inside their teams
  instead of cancelling them, and can assemble their team, run teams in parallel and fill team forms (AO M6b, all
  opt-in). Orchestration records are protocol version 2. No change in this package.

### Runtime pin: MCP resources (2026-11-01)

- Pin of `nodestro-runtime` at `1bc3924` (before: `2d55242`): a connected MCP service's listed resources can be read
  through one approved tool, `resources/read` (MCP WP-10). No change in this package.

### Runtime pin: warnings before unattended starts (2026-11-01)

- Pin of `nodestro-runtime` at `2d55242` (before: `a13f894`): `tool_preflight.unattended_tool_issues` warns before a
  schedule, batch, test series or published API whose tool calls the per-call approval rules would refuse (S-2, R1).
  No change in this package.

### Runtime pin: legacy exemption fix (2026-10-31)

- Pin of `nodestro-runtime` at `a13f894` (before: `40e04b4`): the per-call tool approval activation step runs once,
  and removed tools lose their legacy exemption (S-2 security acceptance), plus MCP tools in releases (#51).
  Nothing changes in this package.

### Runtime pin: teams and orchestrator (2026-10-31)

- Pin of `nodestro-runtime` at `40e04b4` (before: `0aee6a9`): output contracts and capabilities (Adaptive
  Orchestration M3), the orchestrator node (M4) and pool selection by capability (M5), stdio MCP servers (#50).
  Nothing changes in this package.

### Runtime pin (2026-10-31)

- Pin of `nodestro-runtime` at `0aee6a9` (before: `4660d37`): step limits (#48), MCP OAuth (#44), local sandbox
  hardening (#47) and the tool approval audit and inbox (#46). No template changes.

### Customer service: revisions through an approval loop (Adaptive Orchestration M1, 2026-10-31)

- `customer-service`: a rejection with feedback now leads back to the reply writer through a loop connection (at most
  three rounds, then the run fails) instead of a separate one-shot revision agent. The reply writer receives
  `{{feedback}}` and `{{previous}}`; texts ×6 updated, the `revise` agent is gone.
- Templates can declare loops as a fourth connection element (`EdgeLoop`); graph checks ignore loop connections when
  looking for cycles and for the way from the start node.
- Pin of `nodestro-runtime` at `4660d37` (before: `8597544`): loop placeholders in the pre-check (runtime #40), budget
  reservations (#43, Orkexa `b85133d`) and run limits (#45).

### Sandbox gateway security fixes (2026-10-31)

- Pin of `nodestro-runtime` at `8597544` (before: `b6b757b`): the sandbox gateway of Nodestro Local Docker parses
  request heads strictly (request smuggling fix, runtime PR #33) and refuses to start sandboxes when the Docker daemon
  cannot enforce resource limits (runtime PR #37). It also carries the tool approval work of runtime PRs #30 to #36.
  Nothing changes in this package.

### Flow kernel, loop connections and MCP tool provenance (2026-10-31)

- Pin of `nodestro-runtime` at `b6b757b` (before: `78d2899`): the engine runs on the `orkexa.flow` kernel (Orkexa
  `456b92f`) and supports loop connections with mandatory limits; MCP tools carry their provenance. Nothing changes
  in this package.

### Nodestro Local Docker and MCP tools (2026-10-31)

- Pin of `nodestro-runtime` at `78d2899` (before: `d2cb987`): the `local-container` profile and the sandbox gateway
  of Nodestro Local Docker, and the runtime side of MCP tools; nothing changes in this package.

### Strict price-mode error codes (2026-10-31)

- Pin of `nodestro-runtime` at `d2cb987` (before: `45e7774`): strict price-mode refusals get their own error codes;
  nothing changes in this package.

### Built-in Linux sandbox (2026-10-31)

- Pin of `nodestro-runtime` at `45e7774` (before: `272e2f6`): the built-in Linux sandbox (Landlock, seccomp and
  resource limits) that the desktop uses automatically for AI-generated tools; nothing changes in this package.

### Model pricing and cost reconciliation (2026-10-31)

- Pin of `nodestro-runtime` at `272e2f6` (before: `c6bc2e5`): the workspace's price catalog, automatic price
  updates, costs priced with the catalog and the strict price mode, and the comparison with the providers' bills
  (PRICING-1); nothing changes in this package.

### Runs stored as running (2026-10-31)

- Pin of `nodestro-runtime` at `c6bc2e5` (before: `51f0a6c`): a run executed by a worker is stored as `running`
  when it starts (plan step PR-12); nothing changes in this package.

### Server settings and tenant secrets (2026-10-31)

- Pin of `nodestro-runtime` at `51f0a6c` (before: `4104176`): server settings validation, encrypted tenant provider
  keys, container calls without bind mounts and an allowlist for tenant model endpoints (plan step PR-12); nothing
  changes in this package.

### Libraries in the Docker sandbox (2026-10-31)

- Pin of `nodestro-runtime` at `4104176` (before: `3a052d1`): an approved Python environment becomes a container image
  in the Docker sandbox (plan step PR-11); nothing changes in this package.

### Jobs and workers (2026-10-31)

- Pin of `nodestro-runtime` at `3a052d1` (before: `8eea1ea`): the job queue, run workers, reaper and run events of
  the server profile (plan step PR-10); nothing changes for the desktop.

### Server storage and identity (2026-10-31)

- Pin of `nodestro-runtime` at `8eea1ea` (before: `d6e75b7`): PostgreSQL storage, tenant workspaces and identity
  records for the server profile (plan steps PR-7 to PR-9); nothing changes for the desktop.

### Sandbox policy (2026-10-31)

- Pin of `nodestro-runtime` at `d6e75b7` (before: `e90c205`): the runtime with the sandbox policy and trust
  classes for tool code (ADR-0006).

### Storage seams (2026-10-31)

- Pin of `nodestro-runtime` at `e90c205` (before: `8ea9a5c`): the runtime with the `DocumentStore` protocol
  (`Store` stays as an alias). No code change here.

Pin of `nodestro-runtime` at `8ea9a5c` (merge of runtime PR #5): adds the operating profiles
(`nodestro_runtime.profile`). `Workspace(data_dir)` is unchanged, so the examples are unaffected; the pin moves so that
the API, which needs the new runtime, can install both packages together.

Platform integration (2026-10-30): pin of `nodestro-runtime` at `ad75859`. That runtime keeps approval comments out of
result nodes and result files and adds the check `check.input_form_only`, which none of the 24 examples triggers. The
examples themselves are unchanged.

Quality round of 2026-10-30 for all 24 examples in all six languages. The template format (`FORMAT_VERSION = 1`),
the public Python API and every template, node, field, sample and test case id are unchanged; existing copies of
examples are not affected (they are independent workflows).

- Data flow: 24 agents in 18 examples read the request with `{{input}}`. As soon as a form value or a file was
  given, the start node's result only listed the form values, so the request text (for example the planned
  production time, the cost rates or the customer's email) never reached them. They now use `{{run.input}}`, which
  holds the form values and the text. A new test runs every example with an attached sample file and checks that
  the text arrives.
- Data flow: agents get what their task needs: the financial review checks the analysis against the extracted
  figures, the SWOT review checks the strategy against the company profile, the savings adviser sees the
  household's details, the construction status report gets the cause analysis, the menu writer gets the dishes
  with their dietary details, and the customer service revision sees the enquiries and the policy.
- Prompts: every agent treats inputs (documents, emails, enquiries) as data whose instructions do not change its
  task. The recruiting example states that screening or ranking applicants is high-risk under the EU AI Act.
- Test cases: checks with reference values of the prepared data (downtime share 4.62 % and 1.42 %, household
  surplus, farm gross margin range, business idea score from 1 to 10, generated pytest tests in the code review).
- Templates are validated when they are loaded: unique ids, connections between existing nodes, valid branch
  handles, no cycles, every node between start and result node, and sample files and test cases that name
  existing fields, samples and nodes.
- Documentation generator: `--root` names the studio checkout and `--check` only reports chapters that are out of
  date; chapters with broken markers are refused, and files are replaced in one step.
- Tests: all 45 test cases run in all six languages and pass their checks for a correct answer; an empty answer
  fails at least one check of every case. Every decision branch and its default, every approval and every
  rejection (stop or revision, required comment) are tested, and result files are checked by their content.
- Pin of `nodestro-runtime` at `b5aa1b3` (before: `b1bae2a`, which already moved the pin of 0.2.0 forward with
  unchanged behavior of the examples). CI uses current actions (Node 24), checks out without stored credentials and
  checks the contents of the built wheel and sdist.
- README, CHANGELOG, PROVENANCE and CI in English.

## 0.2.0 (2026-10-29)

- First version as a repository of its own: extracted from `nodestro` 0.1.0 (commit 15e2076, now
  `nodestro-legacy`) without new features and without changes in behavior. The origin of each file: PROVENANCE.md.
- Dependencies pinned to exact commits (orkexa `cbf6df3d6f727b96924f1ae66e60b469eeef58e6`); the combination tested
  together is listed in `nodestro-studio/platform/versions.json`.
- CI with the repository secret `NODESTRO_READ`.
