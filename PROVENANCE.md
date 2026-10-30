# Provenance

Source: `peterkarlhuber/nodestro` (now `nodestro-legacy`) at commit
`15e20768dea496820d4f8a286720176b47817da7` (merge of PR #14, version 0.1.0). The column "State" compares each file
byte for byte with the original as of the extraction (version 0.2.0); "adapted" names the changed lines (mostly
rewritten imports). Changes after the extraction are recorded in [CHANGELOG.md](CHANGELOG.md) and the Git history.

182 files unchanged, 4 adapted, 8 new.

Folders copied byte for byte (files summarized):

- `src/nodestro_examples/samples/` – 1 file unchanged
- `src/nodestro_examples/templates/` – 25 files unchanged
- `src/nodestro_examples/texts/` – 156 files unchanged

| File | Original | State |
| --- | --- | --- |
| `.github/workflows/ci.yml` | — | new |
| `.gitignore` | — | new |
| `CHANGELOG.md` | — | new |
| `LICENSE` | — | new |
| `README.md` | — | new |
| `pyproject.toml` | — | new |
| `src/nodestro_examples/__init__.py` | `backend/src/nodestro/library/__init__.py` | adapted (+21 −7 lines) |
| `src/nodestro_examples/docs.py` | `backend/src/nodestro/library/docs.py` | adapted (+3 −3 lines) |
| `src/nodestro_examples/py.typed` | — | new |
| `src/nodestro_examples/samples.py` | `backend/src/nodestro/library/samples.py` | adapted (+9 −8 lines) |
| `tests/test_runs.py` | `backend/tests/test_runs.py` | adapted (+107 −315 lines) |
| `tests/test_templates.py` | — | new |
