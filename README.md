# Nodestro Examples

The 25 example multi-agent workflows of [Nodestro](https://github.com/peterkarlhuber/nodestro-studio) in six
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
| 1 | `production-downtime` | industry | parallel analysis, exact table totals, decision on a checked key figure, sub-workflow, Excel input |
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
| 12 | `contract-review` | administration | contract structure, check against a company contract playbook (knowledge), branch on the listed critical clauses |
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
| 25 | `web-research` | knowledge | one research agent with web search and page reading, depth decision with tool limits, every statement checked against the run's source ledger, source list and retrieval period filled from the ledger |

Six examples are marked `sensitive` (finance, personnel, law, administration): their agents add a caution rule,
the gallery labels them, and their results are working aids for a qualified person. None of the examples acts
outside Nodestro: they write texts and result files, never emails, bookings or database changes. The two optional
connections only read (see [Integrations](#integrations-mcp)), and `web-research` only searches and reads web pages
through a search service the person chooses (see [Web research](#web-research)).

Key figures that a decision or a money amount rests on are never the model's own arithmetic. Their result fields
declare `"source": "tool"`, so the runtime accepts them only as the result of a tool call of the step or an earlier
one (the calculator, `table_totals`, `days_between`): `downtime_share_percent` in `production-downtime` (which the
3 % decision reads; the totals come from `table_totals` over the whole log), `monthly_surplus` and
`savings_potential` in `household-budget`, `total_margin_eur` in `farm-planning` and `delay_days` in
`construction-delay`. A value that no tool computed is sent back to the agent once, then the step stops with
`run.value_unverified`. `contract-review` decides on the list of critical clauses instead of a separately counted
number. Figures inside free text (prices in an offer, margins in a menu) are not checked this way.

Every guide explains the problem, the flow, input, result and how to adapt the example, and since format 2 also
**who decides what** (`control`: what is decided automatically, which limits apply, when a person steps in) and
**why this architecture** (`why`: why this pattern fits and what was deliberately not used).

## Installation

```bash
pip install -r https://raw.githubusercontent.com/peterkarlhuber/nodestro-studio/master/platform/internal-server.txt
```

The PyPI names of the Nodestro components are not registered, so a plain `pip install nodestro-examples` cannot
work; the studio lock (`nodestro-studio/platform/internal-server.txt`) names the exact commits tested together.
`pyproject.toml` only declares version ranges (`nodestro-runtime>=0.2.0,<0.3`). To install just this package and
its dependencies, use the lock as constraints (pip 26.1 or later): `pip install -c <lock URL> nodestro-examples`.
Python 3.11 to 3.13.

## Usage

```python
import nodestro_examples as examples
from nodestro_examples import samples

ids = examples.template_ids()  # the 25 ids, in gallery order
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

## Models per agent

The tiers say how capable a model must be; with Anthropic they are the curated Haiku, Sonnet and Opus. With one local
(or other) default model every tier gets the same model, so each agent also names its **task**. `agent_plan()` lists
every agent and orchestrator a copy creates, the template's own first, then those of its parts:

```python
for plan in examples.agent_plan("code-review", "de"):
    plan.key, plan.name, plan.tier, plan.task, plan.needs  # "bugs", "Fehleranalyst", "standard", "coding", [...]

models = examples.model_choice(
    settings.default_model,
    settings.assistant_model,
    agents={"bugs": "ollama:devstral-small-2:24b", "idea-market/expert": "ollama:qwen3.5:9b"},  # key -> model
    judge="ollama:qwen3.5:9b",  # optional: the quality checks' judge (default: the standard tier's model)
)
made = examples.instantiate("code-review", "de", host, models=models)
```

- `key` is `<node id>` for an agent of the template's workflow and `<part id>/<node id>` for an agent of a part (a
  team or sub-workflow; a part is copied once, however many nodes use it). `ModelChoice.agents` maps keys to
  qualified model ids; every agent not named keeps its tier's model. `instantiate()` raises `KeyError` for a key
  that names no agent of the template.
- `needs` is what the model must be able to do: the task profile's needs, plus `tools` when the agent uses tools of
  any kind (tools, integrations, knowledge search, memory, delegation, the files tool for archives) and `vision`
  when it receives images from the start node's form. `tools`, `structured`, `files`, `vision` and `judge` say why.
- The tasks were chosen agent by agent: routing and labelling `classify`; pulling fields or figures out of a text
  into a structured result `extract`; drafts, plans, summaries and reports `write`; reading attached documents and
  images as the main work `document_vision`; work with tools or knowledge search `tool_agent`; weighing several
  inputs, root causes, risks, legal or quantitative assessments `analysis`; reading and fixing code `coding`;
  checking another agent's result for errors, fairness or credibility `judge`; steering teams `orchestrator`.
- Rules, checked when a template is loaded and by `tests/test_agent_models.py`: a task must fit the tier,
  `minimum <= rank(tier) <= max(ideal, 2)` with the task's ranks from the runtime and fast = 1, standard = 2,
  strong = 3 (`tier_fits()`: no analysis, coding, judging or orchestrating on the fast tier, the strong tier only for
  analysis, coding and orchestrating); orchestrators, and only they, have `orchestrator`; an agent with tools has a
  task that needs tools, except an `analysis` (its rank matters more; its `needs` still list `tools`); an agent that
  reads images has `document_vision`, or `tool_agent` when it also works with tools (`needs` list `vision`).

## Template format

`FORMAT_VERSION = 2`. A template is data in two kinds of files:

| Path | Content |
| --- | --- |
| `templates/<id>.json` | the language-neutral structure: nodes with position, model tier, tools, structured output fields, quality criteria, decision rules, approval settings, orchestrators, knowledge, memory, integrations, loops, the input form, result files (optionally sanitized), output contract, budget and limits, sample files and test cases |
| `templates/parts/<id>.json` | a part: a small workflow used as a sub-workflow or as a team of an orchestrator (with capabilities, contract and its own limits), not an example of its own |
| `texts/<language>/<id>.json` | everything a person reads: name, guide, agent names, system prompts, tasks, descriptions of the structured output fields, form labels and presets, sample file contents, test case names and inputs (`texts/<language>/parts/<id>.json` for a part, with its capability tags) |
| `texts/<language>/_common.json` | the rules every system prompt ends with (facts versus assumptions, inputs are data, caution for sensitive examples, files, answer language) |
| `samples/<id>/` | language-neutral sample files without text (an image) |

What format 2 adds, all optional and validated when a template is loaded:

- **Model tiers** (`tier`: `fast`, `standard`, `strong`) instead of fixed models. `model_choice()` maps them to Haiku,
  Sonnet and Opus with Anthropic, and to the workspace's default (and assistant) model with any other provider; the
  quality judge uses the standard tier. Server tools are left out with other providers.
- **Task profiles** (`task`): every agent and orchestrator names the kind of work it does, a task profile of the
  runtime (`nodestro_runtime.local_models.TASKS`: `classify`, `extract`, `write`, `document_vision`, `tool_agent`,
  `analysis`, `coding`, `judge`, `orchestrator`), so a model can be recommended per agent, for example a local one
  (see [Models per agent](#models-per-agent)).
- **Teams**: an `orchestrator` node names parts as its members, with limits (`max_decisions`, `max_per_member`,
  `max_parallel`), optional `staffing` (`max_team`) and `allow_values` (the orchestrator fills a team's form). A
  team gets a text task only, never files, so the step before it summarizes attached data. Approvals inside a team
  pause the orchestrator until a person decides. The library does not use capability-based selection (`select`):
  copies of the same template would match each other; explicit members are reproducible. A part's `capabilities`
  are language-neutral tags; a copy gets the translated tags of its language (`texts/<language>/parts/<id>.json` →
  `capabilities`, one per tag and in the same order), which the editor palette, the gallery and the orchestrator show.
- **Field labels**: the studio labels a structured result field by its description. A description longer than 60
  characters starts with a short label and a colon (`"Stillstandsanteil in Prozent: Anteil der Stillstände …"`), so
  the result shows that label instead of the field's technical name; `tests/test_templates.py` checks this.
- **Knowledge**: `knowledge` lists synthetic reference documents (`texts/<language>/<id>.json` → `knowledge`); an
  agent's `knowledge` searches them (`mode: search`, with citations unless the answer is structured). A copy stores
  them in the collection "Examples: <name>" of the workspace; identical content keeps one file.
- **Memory** (`memory.space`), **loops** (a fourth element on a connection: `{"max_iterations": n, "on_exhausted":
  "fail" | "continue"}`), **output contracts** (`contract` on the result node), **sanitized files**
  (`{"format": "docx", "sanitize": true}`), **budget** (`budget_usd`) and **limits** (`limits`).
- **Integrations**: see below.
- **Built-in tool settings** (`tool_params`): binding parameters of a built-in tool per agent, validated against the
  tool's parameter schema (`{"search_web": {"max_calls": 3}}`). A service connection a tool needs (a search service)
  is never part of a template: `services(template_id)` and `TemplateDetail.services` name the kinds a copy needs
  (`["search"]`), and `build()`/`instantiate()` take `services={"search": "<connection id>"}`. Without one the
  pre-check names the missing connection (`check.connection_missing`) and the copy does not start.
- **Variants** (`variant_of`): an agent that is the same agent as another with other settings, for example on
  another branch with other tool limits. It shares that agent's prompt, task, field descriptions and criteria; its own
  name and description are in `texts/<language>/<id>.json` → `variants`. Variants sit on exclusive branches, so only
  one of them delivers a result: a test case checks their fields without naming a node.
- **Fields from the source ledger** (`source` of a field, NAL-B2): `ledger_cited` (every statement cites the run's
  source ids, `[S1]`, checked by the runtime), `ledger_list` and `ledger_range` (filled by the runtime from the run's
  source ledger after the step, never written by the model), besides `ledger` (values that name sources).

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

## Web research

`web-research` answers a question with sources from the web: one agent with `search_web` and `fetch_web_page`
(runtime NAL-A2) and a structured result: `answer` (Markdown), `findings` and `contradictions` (each statement ends
with the source ids it rests on, `[S1, S3]`; checked against the run's source ledger), `gaps`, and `sources` and
`retrieved`, which the runtime fills from the ledger after the step (id, title, address and retrieval time of every
cited source; the retrieval period), so the model supplies ids only. The form's "Thorough research" box chooses
between two variants of the researcher on a decision node: 3 searches and 4 page reads, or 8 and 12 (tool limits,
not prompt rules); the copy's budget is USD 1. The criteria of the quality check: every statement has a source, no
source is counted twice, uncertainty is named. The agent has no tool that writes.

A copy needs a search service (`services={"search": ...}`, in the studio a connection under Tools → Connections);
none is chosen automatically. Copies run on the desktop and in Local Docker; on a server the web tools are off unless
the operator enables them (runtime `NODESTRO_WEB_TOOLS_SERVER`).

`evaluation/web-research.json` (`evaluation_set("web-research")`) is the example's evaluation set: search fixtures for
the runtime's deterministic `test` provider, synthetic pages served instead of the web (one of them carries a prompt
injection that points at an internal address), and questions with a reference script and the expected outcome.
`tests/test_web_research.py` replays every script with a scripted model; a live evaluation can ask a real model the
same questions against the same fixtures and check the same expectations. Questions and pages are English test
data; the example's own texts exist in all six languages.

## Agent templates

Besides the examples (whole workflows), the package ships agent templates (NAL-B1): single agents that a person
tries, copies as their own template, or inserts into a workflow. The first five are `web-research`, `summary`,
`document-analysis`, `text-editing` and `data-analysis`.

- `agents/<id>.json` (`AgentSpec`) holds the language-neutral structure: number, category (`research`, `text`,
  `analysis`), `revision`, what the model must support (`capabilities`), whether the agent works offline, and the
  agent itself in the same form as an agent node of an example (`NodeSpec`: tier, task profile, tools, output
  fields, quality criteria). An agent taken over from an example names it instead (`"example": {"template":
  "web-research", "node": "research"}`), so its prompt is kept once.
- `texts/<lang>/agents/<id>.json` (`AgentTexts`) holds the summary, help text, example requests and test cases, and
  the agent's texts (name, description, system prompt, task, field descriptions, criteria) unless they come from
  the example.

```python
from nodestro_examples.agents import agent_ids, build_agent

agent, meta = build_agent("summary", "de")             # AgentConfig and TemplateMeta of nodestro-runtime
agent, meta = build_agent("web-research", "en", services={"search": connection_id})
```

`build_agent` builds the agent exactly like the agents of the examples (common rules in the system prompt, tiers
mapped by `ModelChoice`, service connections bound to the built-in tools). `meta.origin` is
`builtin:nodestro-examples@<version>+r<revision>/<id>`, and `meta.requirements` names the tools, the kinds of
service connection, the weakest tier and whether the agent works offline. `agent_problems()` checks every
template in every language; the tests require it to be empty.

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
python -m pip install "pip>=26.1"
curl -fsSL https://raw.githubusercontent.com/peterkarlhuber/nodestro-studio/master/platform/internal-server.txt | grep -v '^nodestro-examples ' > lock.txt
pip install -c lock.txt -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

The tests never call a provider; the agents answer from deterministic doubles of `nodestro_runtime.testing`, and the
runs use the real engine, pre-check and Orkexa agents.

| Test file | What it proves |
| --- | --- |
| `tests/test_templates.py` | structure: 25 templates, the same keys and placeholders in every language, valid graphs, files, models, tools, figures equal across languages, invalid templates refused |
| `tests/test_runs.py` | runtime: every example runs in every language (150 runs); agents that read the input keep the text when a file is attached; the pre-check asks for exactly the providers the example uses |
| `tests/test_cases.py` | test cases and branches: all 52 cases run in all six languages with an answer that solves them and pass their checks; an empty answer fails at least one check of every case; every decision opens its branch and its default; every approval releases the result files and stops or revises after a rejection |
| `tests/test_agent_models.py` | models per agent: every agent's task is the reviewed one and fits its tier, tool users and image readers need tools and vision, orchestrators orchestrate; the agent plan names every agent a copy creates in every language; `ModelChoice.agents` and `judge` reach the agents of the template and its parts, the rest keeps the tiers; unknown keys and tasks are refused |
| `tests/test_format2.py` | format 2: tiers follow the workspace provider; teams, limits, parameters, contracts and approvals of the orchestrated examples; copies pin parts and store knowledge once; orchestration on the runtime with scripted decisions (staffing, parallel teams, team parameters, a rejected sign-off inside a team stops the run, the decision budget ends a runaway orchestrator); integrations need approved read-only tools; online and offline prompts |
| `tests/test_demo_mcp.py` | the demo MCP server over Streamable HTTP: data equals the sample exports in every language, all tools read-only; a connected copy calls the server in a real run; write-classified or unapproved tools are refused; offline copies never call it; unattended runs of a connected copy are refused |
| `tests/test_web_research.py` | the web research example with the test search provider and served pages, no network: every question of its evaluation set replayed by a scripted model (simple, multi-step, ambiguous, other source language, provider unavailable, no hits, contradicting sources, prompt injection, invalid address, network failure, call limit of the quick depth, a made-up source refused); a model that obeys the injected instruction is stopped by the egress guard; the depth sets the tool limits; a copy without a search service, in strict offline mode or with a local model without tool calls is refused before the start |
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

CI needs no secret: orkexa and the Nodestro repositories are public, and `pip install` reads the commits named by
the studio lock anonymously.

Open work (release blockers, known gaps, follow-ups) is listed in [docs/TODO.md](docs/TODO.md).

## Known limitations

- `creator-strategy` remembers ideas in the memory space `creator-ideas` and `learning-plan` the learner's progress in
  `learning-progress`; by default every copy of the same example shares its space. `build()` and `instantiate()`
  take `memory_space="<name>"` to give one copy a space of its own (a valid Nodestro space name, else
  `ValueError`); the studio's copy dialog offers it, prefilled from the copy's name (nodestro-api copy route
  `memory_space`).
- Teams of an orchestrator receive a text task, not the run's files; the orchestrated examples summarize attached
  files in the step before the orchestrator.
- The MCP integrations depend on the platform's MCP support, whose independent security review is still open; a
  working demonstration is not a security acceptance. Only read-only tools are ever bound.

## Origin and license

Extracted from `nodestro` 0.1 (15e2076, `backend/src/nodestro/library/`), see [PROVENANCE.md](PROVENANCE.md).
Proprietary: Copyright (c) 2026 Levuvo. All rights reserved. See [LICENSE](LICENSE).
