"""The shipped Agent Skills (NAL-B3): two families in six languages, read byte for byte, valid by the spec."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

from nodestro_runtime.schemas import LANGUAGES
import pytest

from nodestro_examples import skills

ROOT = Path(skills.__file__).parent / "skills"


def _orkexa_skills() -> ModuleType | None:
    try:
        return importlib.import_module("orkexa.skills")
    except ImportError:
        return None


def test_two_families_ship_in_every_language() -> None:
    assert skills.SKILL_FAMILIES == ("8d-problem-solving", "research-method")
    assert set(skills.SKILL_LANGUAGES) == set(LANGUAGES)
    expected = sorted(
        f"{family}-{language.lower()}" for family in skills.SKILL_FAMILIES for language in skills.SKILL_LANGUAGES
    )
    assert skills.skill_names() == expected
    assert "research-method-pt-br" in expected and "8d-problem-solving-de" in expected


def test_the_skills_have_no_problems() -> None:
    assert skills.skill_problems() == []


def test_files_are_the_exact_bytes() -> None:
    files = skills.skill_files("8d-problem-solving-en")
    assert set(files) == {"SKILL.md", "references/report-template.md"}
    assert files["SKILL.md"] == (ROOT / "8d-problem-solving-en" / "SKILL.md").read_bytes()
    assert set(skills.skill_files("research-method-de")) == {"SKILL.md"}
    # A fresh mapping every time: changing it does not change what the next caller gets.
    files.clear()
    assert "SKILL.md" in skills.skill_files("8d-problem-solving-en")


@pytest.mark.parametrize("name", ["unknown", "research-method", "research-method-xx", "../texts", ""])
def test_unknown_names_raise_key_error(name: str) -> None:
    with pytest.raises(KeyError):
        skills.skill_files(name)


def test_every_8d_skill_has_the_report_template() -> None:
    for language in skills.SKILL_LANGUAGES:
        files = skills.skill_files(skills.skill_for("8d-problem-solving", language))
        template = files["references/report-template.md"].decode("utf-8")
        assert all(f"D{step}" in template for step in range(1, 9)), language
        assert "references/report-template.md" in files["SKILL.md"].decode("utf-8")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("de", "research-method-de"),
        ("pt-BR", "research-method-pt-br"),
        ("pt-br", "research-method-pt-br"),
        ("pt", "research-method-pt-br"),
        ("pt_BR", "research-method-pt-br"),
        ("FR", "research-method-fr"),
        ("de-AT", "research-method-de"),
        ("nl", "research-method-en"),
        ("", "research-method-en"),
        (None, "research-method-en"),
    ],
)
def test_skill_for_falls_back_to_english(language: str | None, expected: str) -> None:
    assert skills.skill_for("research-method", language) == expected


def test_skill_for_refuses_an_unknown_family() -> None:
    with pytest.raises(KeyError):
        skills.skill_for("six-sigma", "en")


def test_front_matter_and_metadata() -> None:
    for name in skills.skill_names():
        fields, body = skills.split_front_matter(skills.skill_files(name)["SKILL.md"].decode("utf-8"))
        assert fields["name"] == name and fields["license"] == "LicenseRef-Proprietary"
        metadata = fields["metadata"]
        assert isinstance(metadata, dict) and metadata["revision"] == "1"
        assert skills.skill_for(metadata["family"], metadata["language"]) == name
        assert body.lstrip().startswith("# ")


@pytest.mark.parametrize(
    "text",
    [
        "name: x\n---\n",  # no opening line
        "---\nname: x\n",  # not closed
        "---\nname: &anchor x\n---\n",
        "---\nname: !tag x\n---\n",
        "---\nmetadata: {family: x}\n---\n",
        "---\ndescription: |\n  text\n---\n",
        "---\nname: a: b\n---\n",
        '---\nname: "open\n---\n',
        "---\nname: x\nname: y\n---\n",
        "---\n  family: x\n---\n",
        "---\nmetadata:\n  inner:\n    deep: x\n---\n",
    ],
)
def test_the_front_matter_reader_refuses_other_yaml(text: str) -> None:
    with pytest.raises(ValueError):
        skills.split_front_matter(text)


def test_problems_are_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A copy of the skills with mistakes: each one is reported."""
    for name in skills.skill_names():
        for path, data in skills.skill_files(name).items():
            target = tmp_path / name / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    skill = tmp_path / "research-method-fr" / "SKILL.md"
    skill.write_text(skill.read_text("utf-8").replace('language: "fr"', 'language: "it"'), "utf-8")
    (tmp_path / "research-method-de" / "notes.txt").write_text("x", "utf-8")
    (tmp_path / "research-method-it" / "SKILL.md").unlink()
    monkeypatch.setattr(skills, "_SKILLS", tmp_path)
    skills._names.cache_clear()
    skills._files.cache_clear()
    try:
        problems = skills.skill_problems()
    finally:
        skills._names.cache_clear()
        skills._files.cache_clear()
    assert "research-method-it: missing" in problems
    assert "research-method-it: not a skill folder with a SKILL.md" in problems
    assert any(item.startswith("research-method-de: files outside") for item in problems)
    assert any(item.startswith("research-method-fr: family") for item in problems)


def test_every_skill_is_valid_for_orkexa() -> None:
    """The reference reader of the platform (orkexa.skills) finds no error; skipped while the pinned orkexa
    has no skills module yet."""
    module = _orkexa_skills()
    if module is None:
        pytest.skip("orkexa.skills is not available in the installed orkexa")
    for name in skills.skill_names():
        files = {f"{name}/{path}": data for path, data in skills.skill_files(name).items()}
        package = module.parse_skill(files)
        assert package.directory == name
        errors = [issue for issue in module.validate(package) if issue.severity == "error"]
        assert errors == [], (name, errors)
