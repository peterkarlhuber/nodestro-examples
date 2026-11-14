"""The building blocks (parts) as gallery entries of their own (NAL-B3)."""

from __future__ import annotations

import pytest

import nodestro_examples as library
from nodestro_examples import LANGUAGES


def test_every_part_is_listed_in_every_language() -> None:
    ids = library.all_part_ids()
    assert len(ids) == 14 and list(ids) == sorted(ids)
    used = {part_id for template_id in library.template_ids() for part_id in library.part_ids(template_id)}
    assert used <= set(ids)
    for language in LANGUAGES:
        for summary in library.part_summaries(language):
            assert summary.name and summary.description and summary.agents >= 1
            assert summary.language == language
            # Every listed part is used by a template, and those templates really run it.
            assert summary.templates
            assert all(summary.id in library.part_ids(template_id) for template_id in summary.templates)


def test_the_detail_previews_the_workflow_a_copy_gets() -> None:
    detail = library.part_detail("idea-market", "en")
    assert detail.workflow.name == detail.name
    assert detail.workflow.capabilities == detail.capabilities
    with pytest.raises(KeyError):
        library.part_detail("nope", "en")


class _Host:
    def __init__(self) -> None:
        self.saved: list[str] = []

    def save_workflow(self, workflow: library.WorkflowIn) -> tuple[str, int | None]:
        self.saved.append(workflow.name)
        return f"wf_{len(self.saved)}", 1

    def add_knowledge(self, data: bytes, **kwargs: object) -> str:
        raise AssertionError("parts use no knowledge files")


def test_a_copy_saves_inner_parts_first_and_returns_the_part_unsaved() -> None:
    host = _Host()
    made = library.instantiate_part("idea-risks", "de", host)
    assert host.saved == [] and made.parts == {}
    assert made.workflow.name == library.part_texts("idea-risks", "de").name


def test_inner_parts_are_saved_first(monkeypatch: pytest.MonkeyPatch) -> None:
    # No shipped part runs another part today; a nested one is copied first and pinned to its saved version.
    monkeypatch.setattr(library, "_part_closure", lambda part_id: ["idea-market", part_id])
    host = _Host()
    made = library.instantiate_part("idea-risks", "en", host)
    assert host.saved == [library.part_texts("idea-market", "en").name]
    assert made.parts == {"idea-market": ("wf_1", 1)}
