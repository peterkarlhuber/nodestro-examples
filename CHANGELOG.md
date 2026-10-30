# Changelog

## Unreleased

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
