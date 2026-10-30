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
| 2 | `quality-8d` | industry | 8D chain, decision, approval, structured report, knowledge proposals |
| 3 | `supplier-comparison` | industry | parallel cost and risk analysis, offers as PDF, Word and Excel |
| 4 | `sme-swot` | business | parallel SWOT, TOWS strategy, structured critical review |
| 5 | `financial-analysis` | business | figures recalculated with the calculator, structured review |
| 6 | `blog-article` | customers | editorial chain with a fast model, quality check, text statistics |
| 7 | `sales-offer` | customers | input form, calculation, quality check, approval before sending |
| 8 | `customer-service` | customers | triage, deadline tool, escalation branch, approval with revision |
| 9 | `hr-recruiting` | administration | job advert and interview guide, fairness review, revision branch |
| 10 | `research-hypotheses` | knowledge | hypotheses, methods critique on pilot data, experiment plan |
| 11 | `code-review` | knowledge | parallel bug and security review, fix with tests, ZIP input |
| 12 | `contract-review` | administration | contract structure, plain-language explanation, critical-clause branch |
| 13 | `learning-plan` | knowledge | form value (week), course material as input, parallel tutor and quiz |
| 14 | `household-budget` | private | budget recalculation, savings, structured reality check |
| 15 | `travel-plan` | private | input form, date tool, abroad branch from a form value |
| 16 | `business-idea` | business | three parallel experts and a scoring jury |
| 17 | `creator-strategy` | customers | persistent memory, statistics as images or CSV |
| 18 | `real-estate` | business | yield calculation, listing and floor plan as input |
| 19 | `construction-delay` | industry | schedule analysis, cause classification, approval before reporting |
| 20 | `restaurant-menu` | business | dishes, food cost calculation, menu with quality check |
| 21 | `farm-planning` | industry | crop rotation against rules, gross margins, structured plausibility check |
| 22 | `club-event` | private | schedule and budget in parallel, board paper |
| 23 | `nonprofit-campaign` | private | campaign, impact model, credibility review |
| 24 | `citizen-inquiry` | administration | concerns, rules from the given information only, draft reply |

Six examples are marked `sensitive` (finance, personnel, law, administration): their agents add a caution rule,
the gallery labels them, and their results are working aids for a qualified person. None of the examples acts
outside Nodestro: they write texts and result files, never emails, bookings or database changes.

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

`POST /api/library/{id}/copy` of the API does exactly this: it copies the parts as workflows of their own, pins the
sub-workflow nodes to their first version and saves the copy as an ordinary workflow. Later changes to the library
never change a copy. With `"tests": true` the copy also gets the example's test cases as a test series; nothing is
run until a person starts it.

## Template format

`FORMAT_VERSION = 1`. A template is data in two kinds of files:

| Path | Content |
| --- | --- |
| `templates/<id>.json` | the language-neutral structure: nodes with position, model, tools, structured output fields, quality criteria, decision rules, approval settings, the input form, result files, sample files and test cases |
| `templates/parts/<id>.json` | a part: a small workflow used as a sub-workflow, not an example of its own |
| `texts/<language>/<id>.json` | everything a person reads: name, guide, agent names, system prompts, tasks, form labels and presets, sample file contents, test case names and inputs |
| `texts/<language>/_common.json` | the rules every system prompt ends with (facts versus assumptions, inputs are data, caution for sensitive examples, files, answer language) |
| `samples/<id>/` | language-neutral sample files without text (an image) |

The models (`TemplateSpec`, `TemplateTexts`, …) are strict: unknown keys are refused, and a template is checked when
it is loaded (unique node ids, connections between existing nodes, valid branch handles, no cycles, every node on a
way from the start node to the result node, sample files and test cases that name existing fields, samples and
nodes). The ids of templates, nodes, fields, samples and test cases are technical and the same in every language.

In a task, `{{node:<id>}}` names the result of another node and becomes the placeholder of that node's name in the
language (`{{Root cause analyst}}`). Agents that read the request use `{{run.input}}`: as soon as a form value or a
file is given, the start node's own result only lists the form values, while `{{run.input}}` holds the values and the
free text together.

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
| `tests/test_cases.py` | test cases and branches: all 45 cases run in all six languages with an answer that solves them and pass their checks; an empty answer fails at least one check of every case; every decision opens its branch and its default; every approval releases the result files and stops or revises after a rejection |
| `tests/test_docs.py` | the generated documentation chapter: complete, idempotent, handwritten text kept, broken markers refused |

What the tests do not prove: the quality of real model answers. A simulated run shows that data flows, decisions,
approvals, files and checks work; whether a model calculates the downtime share correctly shows only a run with a
provider, for example by starting a copy's test series in the studio (it costs tokens).

After changing a template, regenerate the example chapter of the studio documentation:

```bash
python -m nodestro_examples.docs --root ../nodestro-studio  # or `make example-docs` in nodestro-studio
python -m nodestro_examples.docs --root ../nodestro-studio --check  # exit code 1 while a chapter is out of date
```

To add an example: add `templates/<id>.json` with the next number and a `texts/<language>/<id>.json` for every
language, then run the tests; they name every missing key, placeholder or reference.

CI needs the repository secret `NODESTRO_READ`: a token with read access to orkexa and the Nodestro repositories,
used only for `pip install` of the pinned dependencies and never stored in the checkout or the package.

## Known limitations

- The quality judge of agents with criteria uses `claude-sonnet-5-5` (`JUDGE_MODEL`), so those examples need an
  Anthropic key even after their agents are switched to another provider; change the judge in the agent's quality
  settings of the copy.
- When an approval is decided with a comment, the comment reaches the result node as an extra result: the run's
  result becomes an object with one entry per name, and checks on fields of the approved result no longer match.
  Approve test series runs without a comment.
- `creator-strategy` remembers ideas in the memory space `creator-ideas`; every copy of the example shares it.

## Origin and license

Extracted from `nodestro` 0.1 (15e2076, `backend/src/nodestro/library/`), see [PROVENANCE.md](PROVENANCE.md).
MIT, see [LICENSE](LICENSE).
