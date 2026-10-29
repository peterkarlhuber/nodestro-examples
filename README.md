# Nodestro Examples

Die 24 Beispiel-Workflows von [Nodestro](https://github.com/peterkarlhuber/nodestro-studio) in sechs Sprachen (de,
en, es, fr, pt-BR, it), mit Beispieldateien und Testfällen. Die Galerie im Studio und `GET /api/library` der
[API](https://github.com/peterkarlhuber/nodestro-api) zeigen sie an; nichts wird automatisch angelegt, eine Kopie
entsteht erst auf Wunsch.

Teil der Nodestro-Plattform; den Überblick gibt
[PLATTFORM.md](https://github.com/peterkarlhuber/nodestro-studio/blob/master/docs/PLATTFORM.md).

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `src/nodestro_examples/templates/` | Struktur jedes Beispiels (Knoten, Verbindungen, Formular, Testfälle), sprachneutral |
| `src/nodestro_examples/texts/<sprache>/` | Namen, Prompts, Beschreibungen und Testeingaben je Sprache |
| `src/nodestro_examples/samples.py`, `samples/` | Beispieldateien (CSV, XLSX, DOCX, PDF, Bilder), zum Teil zur Laufzeit erzeugt |
| `src/nodestro_examples/docs.py` | erzeugt den Beispielteil des Doku-Kapitels „Beispiele“ im Studio |

```python
import nodestro_examples as examples

ids = examples.template_ids()  # die 24 Beispiele
workflow = examples.build("financial-analysis", "de")  # ein unabhängiger Workflow (WorkflowIn) auf Deutsch
```

## Entwicklung

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

`tests/test_templates.py` prüft Struktur und Texte (gleiche Schlüssel in allen Sprachen, gültige Workflows,
Beispieldateien). `tests/test_runs.py` führt jedes Beispiel in jeder Sprache mit simulierten Modellen auf der Runtime
aus (24 × 6 Läufe) und prüft die Testfälle mit ihren Beispieldateien.

Nach einer Änderung an einem Beispiel im Studio `make example-docs` ausführen; ein Test des Studios schlägt sonst fehl.

Die CI braucht das Repository-Secret `NODESTRO_READ` (Lesezugriff auf orkexa und die nodestro-Repositories).

## Herkunft und Lizenz

Aus `nodestro` 0.1 (15e2076, `backend/src/nodestro/library/`) herausgelöst, siehe [PROVENANCE.md](PROVENANCE.md).
MIT, siehe [LICENSE](LICENSE).
