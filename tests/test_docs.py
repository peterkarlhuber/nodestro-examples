"""The generated example chapter: complete in every language, idempotent, and safe for handwritten text."""

from __future__ import annotations

from pathlib import Path

import pytest

import nodestro_examples as library
from nodestro_examples import docs

HANDWRITTEN = "# Examples\n\nHandwritten introduction.\n\n"


def chapters(root: Path, text: str = HANDWRITTEN) -> None:
    for language in docs.LANGUAGES:
        folder = root / docs.CHAPTERS / language
        folder.mkdir(parents=True)
        (folder / "beispiele.md").write_text(text, encoding="utf-8")


@pytest.mark.parametrize("language", docs.LANGUAGES)
def test_every_example_has_a_section_in_every_language(language: str) -> None:
    part = docs.render(language)
    assert part.startswith(docs.START) and part.endswith(docs.END)
    for template_id in library.template_ids():
        summary = library.summary(template_id, language)
        assert f"## {summary.number} · {summary.name} {{#{template_id}}}" in part
    assert docs.render(language) == part


def test_only_the_generated_part_changes_and_a_second_run_changes_nothing() -> None:
    once = docs.updated(HANDWRITTEN + "Closing words.\n", "en")
    assert once.startswith(HANDWRITTEN + "Closing words.") and docs.END in once
    before = HANDWRITTEN + f"{docs.START}\nOUTDATED PART\n{docs.END}\n\nAfter the part.\n"
    replaced = docs.updated(before, "en")
    assert replaced.startswith(HANDWRITTEN) and replaced.endswith(f"{docs.END}\n\nAfter the part.\n")
    assert "OUTDATED PART" not in replaced
    assert docs.updated(replaced, "en") == replaced


@pytest.mark.parametrize(
    "broken",
    [
        f"{docs.START}\nno end",
        f"no start\n{docs.END}",
        f"{docs.END}\n{docs.START}",
        f"{docs.START}\n{docs.END}\n{docs.START}\n{docs.END}",
    ],
)
def test_broken_markers_are_refused(broken: str) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        docs.updated(broken, "de")


def test_the_command_writes_checks_and_reports_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    chapters(tmp_path)
    assert docs.main(["--root", str(tmp_path), "--check"]) == 1
    assert docs.main(["--root", str(tmp_path)]) == 0
    assert docs.main(["--root", str(tmp_path), "--check"]) == 0
    english = tmp_path / docs.CHAPTERS / "en" / "beispiele.md"
    assert english.read_text(encoding="utf-8").startswith(HANDWRITTEN)
    assert not [path for path in english.parent.iterdir() if path.name.endswith(".tmp")]
    english.write_text(f"{docs.START}\n", encoding="utf-8")
    assert docs.main(["--root", str(tmp_path)]) == 2
    assert english.read_text(encoding="utf-8") == f"{docs.START}\n"
    assert docs.main(["--root", str(tmp_path / "missing")]) == 2
    assert "error:" in capsys.readouterr().err
