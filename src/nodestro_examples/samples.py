"""Sample files and test cases of the example library.

A sample file is synthetic data for a file field of a template, so an example with file
inputs can be tried without own documents. Most samples are built on request from the texts
of a language with the writers of result files: Markdown becomes PDF (:func:`nodestro_runtime.reports.to_pdf`)
or Word (:func:`nodestro_runtime.office.to_docx`), rows become CSV or Excel (:func:`nodestro_runtime.office.to_xlsx`),
a set of texts becomes a ZIP archive. A file without text, such as an image, is read from
``samples/<template id>/``. The same template and language always give the same bytes.

The test cases of a template become an ordinary test series (:mod:`nodestro_api.benchmarks`) when a
copy is made with them: their sample files are stored as input files of the copy (they stay as
long as a test case references them), and the checks name the result fields of that copy.
Nothing is run: starting the test series is the user's decision.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import Any
import zipfile

from nodestro_runtime.graph import data_sources
from nodestro_runtime.office import to_docx, to_xlsx
from nodestro_runtime.reports import csv_bytes, to_pdf
from nodestro_runtime.reports import file_name as safe_file_name
from nodestro_runtime.schemas import ConditionRule, WorkflowIn

from . import _ROOT, SampleSpec, structure, texts

#: The date written into generated Office files, so they are the same every time.
_FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)
_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

MEDIA_TYPES: dict[str, str] = {
    "txt": "text/plain; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "zip": "application/zip",
    "png": "image/png",
}


def _sample(template_id: str, sample_id: str) -> SampleSpec:
    for sample in structure(template_id).samples:
        if sample.id == sample_id:
            return sample
    raise KeyError(sample_id)


def file_name(template_id: str, sample_id: str, language: str) -> str:
    sample = _sample(template_id, sample_id)
    return safe_file_name(texts(template_id, language).samples[sample_id].name, sample_id, sample.format)


def _records(rows: list[list[Any]]) -> list[dict[str, Any]]:
    header = [str(cell) for cell in rows[0]]
    return [dict(zip(header, row, strict=True)) for row in rows[1:]]


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            info = zipfile.ZipInfo(path, date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content.encode("utf-8"))
    return buffer.getvalue()


def _content(format: str, name: str, content: Any, *, template_id: str = "", file: str | None = None) -> bytes:
    """The bytes of a file in ``format`` built from its content (or read from ``samples/``)."""
    if file is not None:
        return (_ROOT / "samples" / template_id / file).read_bytes()
    if format in ("md", "txt"):
        return str(content).encode("utf-8")
    if format == "pdf":
        return to_pdf(str(content), name)
    if format == "docx":
        return to_docx(str(content), name, _FIXED)
    if format == "csv":
        return csv_bytes([[str(cell) for cell in row] for row in content])
    if format == "xlsx":
        return to_xlsx({sheet: _records(rows) for sheet, rows in content.items()}, name, _FIXED)
    if format == "json":
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
    if format == "zip":
        return _zip({str(path): str(item) for path, item in content.items()})
    raise KeyError(format)  # pragma: no cover - a static format without a file


def render(template_id: str, sample_id: str, language: str) -> tuple[str, str, bytes]:
    """File name, media type and bytes of a sample file in one language; ``KeyError`` if unknown."""
    sample = _sample(template_id, sample_id)
    text = texts(template_id, language).samples[sample_id]
    name = file_name(template_id, sample_id, language)
    data = _content(sample.format, text.name, text.content, template_id=template_id, file=sample.file)
    return name, MEDIA_TYPES[sample.format], data


def render_knowledge(template_id: str, knowledge_id: str, language: str) -> tuple[str, str, bytes]:
    """File name, media type and bytes of a knowledge file of a template in one language."""
    spec = next((item for item in structure(template_id).knowledge if item.id == knowledge_id), None)
    if spec is None:
        raise KeyError(knowledge_id)
    text = texts(template_id, language).knowledge[knowledge_id]
    name = safe_file_name(text.name, knowledge_id, spec.format)
    return name, MEDIA_TYPES[spec.format], _content(spec.format, text.name, text.content)


def sample_ids(template_id: str) -> list[str]:
    return [sample.id for sample in structure(template_id).samples]


def check_path(workflow: WorkflowIn, node_id: str | None, field: str) -> str:
    """The path of a checked field in the run's result.

    The result is the result of the single node that reaches the result node, or an object with
    one entry per node (by name) when several do.
    """
    output = next(node for node in workflow.nodes if node.type == "output")
    sources = data_sources(workflow, output.id)
    if node_id is None or len(sources) < 2:
        return field
    label = next(node.label for node in workflow.nodes if node.id == node_id)
    return f"{label}.{field}" if field else label


def suite_cases(
    template_id: str, language: str, workflow: WorkflowIn, store: Callable[[str, str, bytes], str]
) -> list[dict[str, Any]]:
    """The test cases of a template for a copy (``store`` keeps a sample file, returns its id)."""
    spec = structure(template_id)
    text = texts(template_id, language)
    stored: dict[str, str] = {}
    cases = []
    for case in spec.tests:
        own = text.tests[case.id]
        values: dict[str, Any] = {**own.values, **case.values}
        for sample_id in case.samples:
            if sample_id not in stored:
                stored[sample_id] = store(*render(template_id, sample_id, language))
            field = _sample(template_id, sample_id).field
            values[field] = [*values.get(field, []), stored[sample_id]]
        free = {"default": text.input, "own": own.input, "none": ""}[case.input]
        checks = [
            ConditionRule(
                id=f"check_{number}",
                label="",
                field=check_path(workflow, check.node, check.field),
                operator=check.operator,
                value=check.value,
            ).model_dump()
            for number, check in enumerate(case.checks, start=1)
        ]
        cases.append({"name": own.name, "input": free, "values": values, "checks": checks})
    return cases


def static_files() -> list[Path]:
    """The language-neutral sample files (for tests)."""
    return sorted(path for path in (_ROOT / "samples").rglob("*") if path.is_file())
