# Herkunft

Quelle: `peterkarlhuber/nodestro` (heute `nodestro-legacy`) am Commit
`15e20768dea496820d4f8a286720176b47817da7` (Merge von PR #14, Version 0.1.0). Die Spalte „Stand“ vergleicht jede
Datei byte-genau mit dem Original; „angepasst“ nennt die geänderten Zeilen (meist umgeschriebene Importe).

182 Dateien unverändert, 4 angepasst, 8 neu.

Byte-genau übernommene Ordner (Dateien zusammengefasst):

- `src/nodestro_examples/samples/` – 1 Dateien unverändert
- `src/nodestro_examples/templates/` – 25 Dateien unverändert
- `src/nodestro_examples/texts/` – 156 Dateien unverändert

| Datei | Original | Stand |
| --- | --- | --- |
| `.github/workflows/ci.yml` | — | neu |
| `.gitignore` | — | neu |
| `CHANGELOG.md` | — | neu |
| `LICENSE` | — | neu |
| `README.md` | — | neu |
| `pyproject.toml` | — | neu |
| `src/nodestro_examples/__init__.py` | `backend/src/nodestro/library/__init__.py` | angepasst (+21 −7 Zeilen) |
| `src/nodestro_examples/docs.py` | `backend/src/nodestro/library/docs.py` | angepasst (+3 −3 Zeilen) |
| `src/nodestro_examples/py.typed` | — | neu |
| `src/nodestro_examples/samples.py` | `backend/src/nodestro/library/samples.py` | angepasst (+9 −8 Zeilen) |
| `tests/test_runs.py` | `backend/tests/test_runs.py` | angepasst (+107 −315 Zeilen) |
| `tests/test_templates.py` | — | neu |
