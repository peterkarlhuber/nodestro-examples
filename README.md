# Nodestro Examples

The 24 example multi-agent workflows of [Nodestro](https://github.com/peterkarlhuber/nodestro-studio) in six
languages (de, en, es, fr, pt-BR, it), with synthetic sample files and prepared test cases. The studio gallery and
`GET /api/library` of the [API](https://github.com/peterkarlhuber/nodestro-api) show them; nothing is created
automatically, a workflow only exists once a person copies an example.

Part of the Nodestro platform; [PLATFORM.md](https://github.com/peterkarlhuber/nodestro-studio/blob/master/docs/PLATFORM.md)
gives an overview of all repositories. The package depends only on
[nodestro-runtime](https://github.com/peterkarlhuber/nodestro-runtime) (workflow schemas, file writers) and
pydantic; it has no engine, HTTP API or agent orchestration of its own.

## The examples

| No. | Id | Category | Shows |
| --- | --- | --- | --- |
| 1 | `production-downtime` | industry | parallel analysis, calculator, decision, sub-workflow, Excel input |
| 2 | `quality-8d` | industry | 8D chain, archive of past 8D reports searched with citations, decision, approval, knowledge proposals |
| 3 | `supplier-comparison` | industry | parallel cost and risk analysis, optional read-only ERP connection (MCP) or ERP export, offers as PDF, Word and Excel |
| 4 | `sme-swot` | business | parallel SWOT, TOWS strategy, structured critical review |
| 5 | `financial-analysis` | business | figures recalculated with the calculator, structured review |
| 6 | `blog-article` | customers | structured brief with a fast model, writer with quality check, editor with text statistics |
| 7 | `sales-offer` | customers | input form, calculation, quality check, approval whose rejection sends the offer back for revision |
| 8 | `customer-service` | customers | triage, deadline tool, optional read-only shop connection (MCP) or order export, escalation branch, approval with revision |
| 9 | `hr-recruiting` | administration | job advert and interview guide, fairness gate with revision branch, final approval |
| 10 | `research-hypotheses` | knowledge | orchestrator over four method teams, team parameters set by the orchestrator, study plan |
| 11 | `code-review` | knowledge | parallel bug and security review, fix with tests, ZIP input |
| 12 | `contract-review` | administration | contract structure, check against a company contract playbook (knowledge), critical-clause branch |
| 13 | `learning-plan` | knowledge | persistent memory of the learner's progress, course material as input, parallel tutor and quiz |
| 14 | `household-budget` | private | budget recalculation, savings, structured reality check |
| 15 | `travel-plan` | private | input form, date tool, abroad branch from a form value |
| 16 | `business-idea` | business | orchestrator choosing among five expert teams (in parallel), scoring jury |
| 17 | `creator-strategy` | customers | persistent memory, statistics as images or CSV |
| 18 | `real-estate` | business | yield calculation, listing and floor plan as input |
| 19 | `construction-delay` | industry | orchestrator staffing specialist teams, sign-off inside the claims team, approval before reporting |
| 20 | `restaurant-menu` | business | dishes, food cost calculation, menu with quality check |
| 21 | `farm-planning` | industry | crop rotation against rules, gross margins, structured plausibility check |
| 22 | `club-event` | private | schedule and budget in parallel, board paper |
| 23 | `nonprofit-campaign` | private | campaign, impact model, credibility review that sends the campaign back (at most twice) |
| 24 | `citizen-inquiry` | administration | municipal rules searched with citations, approval with revision, sanitized reply file |

Six examples are marked `sensitive` (finance, personnel, law, administration): their agents add a caution rule,
the gallery labels them, and their results are working aids for a qualified person. None of the examples acts
outside Nodestro: they write texts and result files, never emails, bookings or database changes. The two optional
connections only read (see [Integrations](#integrations-mcp)).

Every guide explains the problem, the flow, input, result and how to adapt the example, and since format 2 also
**who decides what** (`control`: what is decided automatically, which limits apply, when a person steps in) and
**why this architecture** (`why`: why this pattern fits and what was deliberately not used).

## Installation

```bash
pip install "nodestro-examples @ git+https://github.com/peterkarlhuber/nodestro-examples.git@<commit>"
```

The runtime and orkexa are pinned to exact commits; the combination tested together is listed in
`nodestro-studio/platform/versions.json`. Python 3.10 to 3.13.

## Usage

```python
import nodestro_examples as examples
from nodestro_examples import samples

ids = examples.template_ids()  # the 24 ids, in gallery order
card = examples.summary("financial-analysis", "fr")  # what the gallery shows; unknown languages fall back to "en"
detail = examples.detail("quality-8d", "de")  # guide, agents, sample files, test cases and the workflow a copy gets
workflow = examples.build("financial-analysis", "en")  # a new, independent WorkflowIn on every call

# Sub-workflows: save each part first, then point the copy at the saved version.
copies = {part_id: ("wf_123", 1) for part_id in examples.part_ids("production-downtime")}
part = examples.build_part("quality-check", "en")
linked = examples.link_parts(examples.build("production-downtime", "en"), copies)

name, media_type, data = samples.render("supplier-comparison", "offer_a", "es")  # a synthetic sample file
```

For a complete copy use `instantiate()`: it stores the template's knowledge files, saves the parts (teams and
sub-workflows, dependencies first), pins every reference to the saved version and returns the unsaved copy. The host
is anything with `save_workflow()` and `add_knowledge()` (the API's workspace context, or a runtime `Workspace`):

```python
models = examples.model_choice(settings.default_model, settings.assistant_model)  # tiers -> the workspace's models
connections = {"erp": examples.connect("supplier-comparison", "erp", offered)}  # optional; offered: server tools
made = examples.instantiate("supplier-comparison", "de", host, models=models, connections=connections)
host.save_workflow(made.workflow)  # made.parts, made.knowledge, made.connected, made.offline
```

`connect()` raises `IntegrationProblem` unless every tool of the integration is approved by an administrator and
classified as read-only. `POST /api/library/{id}/copy` of the API does exactly this (with `"integrations":
{"erp": "<server id>"}` for a connection) and saves the copy as an ordinary workflow. Later changes to the library
never change a copy. With `"tests": true` the copy also gets the example's test cases as a test series; nothing is
run until a person starts it (refused for connected copies: MCP tools are not allowed in unattended runs).

## Template format

`FORMAT_VERSION = 2`. A template is data in two kinds of files:

| Path | Content |
| --- | --- |
| `templates/<id>.json` | the language-neutral structure: nodes with position, model tier, tools, structured output fields, quality criteria, decision rules, approval settings, orchestrators, knowledge, memory, integrations, loops, the input form, result files (optionally sanitized), output contract, budget and limits, sample files and test cases |
| `templates/parts/<id>.json` | a part: a small workflow used as a sub-workflow or as a team of an orchestrator (with capabilities, contract and its own limits), not an example of its own |
| `texts/<language>/<id>.json` | everything a person reads: name, guide, agent names, system prompts, tasks, form labels and presets, sample file contents, test case names and inputs |
| `texts/<language>/_common.json` | the rules every system prompt ends with (facts versus assumptions, inputs are data, caution for sensitive examples, files, answer language) |
| `samples/<id>/` | language-neutral sample files without text (an image) |

What format 2 adds, all optional and validated when a template is loaded:

- **Model tiers** (`tier`: `fast`, `standard`, `strong`) instead of fixed models. `model_choice()` maps them to Haiku,
  Sonnet and Opus with Anthropic, and to the workspace's default (and assistant) model with any other provider; the
  quality judge uses the standard tier. Server tools are left out with other providers.
- **Teams**: an `orchestrator` node names parts as its members, with limits (`max_decisions`, `max_per_member`,
  `max_parallel`), optional `staffing` (`max_team`) and `allow_values` (the orchestrator fills a team's form). A
  team gets a text task only, never files, so the step before it summarizes attached data. Approvals inside a team
  pause the orchestrator until a person decides. The library does not use capability-based selection (`select`):
  copies of the same template would match each other; explicit members are reproducible.
- **Knowledge**: `knowledge` lists synthetic reference documents (`texts/<language>/<id>.json` → `knowledge`); an
  agent's `knowledge` searches them (`mode: search`, with citations unless the answer is structured). A copy stores
  them in the collection "Examples: <name>" of the workspace; identical content keeps one file.
- **Memory** (`memory.space`), **loops** (a fourth element on a connection: `{"max_iterations": n, "on_exhausted":
  "fail" | "continue"}`), **output contracts** (`contract` on the result node), **sanitized files**
  (`{"format": "docx", "sanitize": true}`), **budget** (`budget_usd`) and **limits** (`limits`).
- **Integrations**: see below.

The models (`TemplateSpec`, `TemplateTexts`, …) are strict: unknown keys are refused, and a template is checked when
it is loaded (unique node ids, connections between existing nodes, valid branch handles, no cycles, every node on a
way from the start node to the result node, sample files and test cases that name existing fields, samples and
nodes). The ids of templates, nodes, fields, samples and test cases are technical and the same in every language.

In a task, `{{node:<id>}}` names the result of another node and becomes the placeholder of that node's name in the
language (`{{Root cause analyst}}`). Agents that read the request use `{{run.input}}`: as soon as a form value or a
file is given, the start node's own result only lists the form values, while `{{run.input}}` holds the values and the
free text together.

## Integrations (MCP)

Two examples can read live data through an MCP server: `supplier-comparison` (integration `erp`, tools
`list_suppliers` and `supplier_scorecard`) and `customer-service` (integration `shop`, tool `get_order`). An
integration is optional. A copy binds its tools only when the person connects it to a server whose tools an
administrator approved as read-only; otherwise the copy works in a labelled offline mode with an exported file (a
sample is included), and both the description and the agent's prompt say which mode the copy is in. Runs without a
person (schedules, test series, batches, published APIs) may not call MCP tools unless an operator sets
`NODESTRO_MCP_UNATTENDED=1`; the examples never ask for that.

`python -m nodestro_examples.demo_mcp --language de` starts a local, read-only demo server on
`http://127.0.0.1:8765/mcp` (desktop: connect it under Tools → Connected services with the consent for a local
development server). It serves exactly the synthetic data of the two sample exports, marked as demo data, and keeps
no state. A real ERP or shop system can take its place when its MCP server offers tools with the same names.

## Sample files

`samples.render()` builds a sample file on request from the texts of a language with the runtime's writers:
Markdown becomes `pdf` or `docx`, rows become `csv` or `xlsx`, a set of texts becomes a `zip` archive, `json`, `md`
and `txt` are written as they are, and `png` comes from `samples/`. Office and ZIP files carry a fixed timestamp, so
the same template and language always give the same bytes. All sample data is fictional and marked as synthetic;
the figures are the same in every language.

## Test cases

A test case (`tests` in the template) has form values, sample files and checks. `samples.suite_cases()` turns the
cases into the cases of a test series for a copy: sample files are stored once as input files of the copy, and each
check becomes a rule on the run's result. When several results reach the result node, a check names its node and
the path becomes `<node name>.<field>` in the copy's language. Checks compare with reference values of the prepared
data where a result is a number (for example the downtime share of 4.62 % or the household surplus of EUR 463).

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

The tests never call a provider; the agents answer from deterministic doubles of `nodestro_runtime.testing`, and the
runs use the real engine, pre-check and Orkexa agents.

| Test file | What it proves |
| --- | --- |
| `tests/test_templates.py` | structure: 24 templates, the same keys and placeholders in every language, valid graphs, files, models, tools, figures equal across languages, invalid templates refused |
| `tests/test_runs.py` | runtime: every example runs in every language (144 runs); agents that read the input keep the text when a file is attached; the pre-check asks for exactly the providers the example uses |
| `tests/test_cases.py` | test cases and branches: all 49 cases run in all six languages with an answer that solves them and pass their checks; an empty answer fails at least one check of every case; every decision opens its branch and its default; every approval releases the result files and stops or revises after a rejection |
| `tests/test_format2.py` | format 2: tiers follow the workspace provider; teams, limits, parameters, contracts and approvals of the orchestrated examples; copies pin parts and store knowledge once; orchestration on the runtime with scripted decisions (staffing, parallel teams, team parameters, a rejected sign-off inside a team stops the run, the decision budget ends a runaway orchestrator); integrations need approved read-only tools; online and offline prompts |
| `tests/test_demo_mcp.py` | the demo MCP server over Streamable HTTP: data equals the sample exports in every language, all tools read-only; a connected copy calls the server in a real run; write-classified or unapproved tools are refused; offline copies never call it; unattended runs of a connected copy are refused |
| `tests/test_docs.py` | the generated documentation chapter: complete, idempotent, handwritten text kept, broken markers refused |

What the tests do not prove: the quality of real model answers. A simulated run shows that data flows, decisions,
approvals, files and checks work; whether a model calculates the downtime share correctly shows only a run with a
provider, for example by starting a copy's test series in the studio (it costs tokens). The orchestrators' decisions
are scripted in the tests: they prove what the engine does with a decision, not which decision a model makes. The
MCP tests use the local demo server, never a real ERP or shop system.

After changing a template, regenerate the example chapter of the studio documentation:

```bash
python -m nodestro_examples.docs --root ../nodestro-studio  # or `make example-docs` in nodestro-studio
python -m nodestro_examples.docs --root ../nodestro-studio --check  # exit code 1 while a chapter is out of date
```

To add an example: add `templates/<id>.json` with the next number and a `texts/<language>/<id>.json` for every
language, then run the tests; they name every missing key, placeholder or reference.

CI needs the repository secret `NODESTRO_READ`: a token with read access to orkexa and the Nodestro repositories,
used only for `pip install` of the pinned dependencies and never stored in the checkout or the package.

Open work (release blockers, known gaps, follow-ups) is listed in [docs/TODO.md](docs/TODO.md).

## Known limitations

- When an approval is decided with a comment, the comment reaches the result node as an extra result: the run's
  result becomes an object with one entry per name, and checks on fields of the approved result no longer match.
  Approve test series runs without a comment.
- `creator-strategy` remembers ideas in the memory space `creator-ideas` and `learning-plan` the learner's progress in
  `learning-progress`; every copy of the same example shares its space.
- Teams of an orchestrator receive a text task, not the run's files; the orchestrated examples summarize attached
  files in the step before the orchestrator.
- The MCP integrations depend on the platform's MCP support, whose independent security review is still open; a
  working demonstration is not a security acceptance. Only read-only tools are ever bound.

## Origin and license

Extracted from `nodestro` 0.1 (15e2076, `backend/src/nodestro/library/`), see [PROVENANCE.md](PROVENANCE.md).
MIT, see [LICENSE](LICENSE).
