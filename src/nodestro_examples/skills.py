"""Shipped Agent Skills (NAL-B3): method instructions an agent loads on demand, in every interface language.

A skill follows the Agent Skills specification (https://agentskills.io/specification): a folder
``skills/<name>/`` with a ``SKILL.md`` (YAML front matter and Markdown instructions) and optional
``references/*.md`` the agent reads when it needs them. There is one skill per family and language, named
``<family>-<language>`` with the language in lowercase (``research-method-pt-br``); the front matter's
``metadata`` names the ``family``, the ``language`` (``pt-BR``) and the ``revision``.

This module only lists and reads the files, byte for byte; storing skills, assigning them to agents and loading
them at run time happen elsewhere. It needs nothing beyond the standard library, so its front matter reader is a
small strict one: flat ``key: value`` lines, one level of ``metadata``, plain or quoted one-line scalars, and no
other YAML feature.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
import re

#: The skill families, in the order a gallery shows them.
SKILL_FAMILIES: tuple[str, ...] = ("8d-problem-solving", "research-method")
#: The languages every family ships in (the interface languages of the examples).
SKILL_LANGUAGES: tuple[str, ...] = ("de", "en", "es", "fr", "it", "pt-BR")
#: The license every shipped skill names.
SKILL_LICENSE = "LicenseRef-Proprietary"

_SKILLS = Path(__file__).parent / "skills"
_SKILL_FILE = "SKILL.md"
_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_KEY = re.compile(r"^([a-z][a-z0-9_-]*):(?: (.*))?$")
_FALLBACK = "en"
_LANGUAGE_BY_TAG = {language.lower(): language for language in SKILL_LANGUAGES} | {"pt": "pt-BR"}
#: Front matter keys of the specification; anything else is reported by :func:`skill_problems`.
_KNOWN_KEYS = frozenset({"name", "description", "license", "compatibility", "metadata", "allowed-tools"})
_METADATA_KEYS = frozenset({"family", "language", "revision"})
#: Limits of the specification for the instructions (lines; about 4 characters per token).
_MAX_LINES = 500
_MAX_TOKENS = 5000

FrontMatter = dict[str, str | dict[str, str]]


def skill_name(family: str, language: str) -> str:
    """The name of a family's skill in one language (``research-method-pt-br``); no check that it exists."""
    return f"{family}-{language.lower()}"


@cache
def _names() -> tuple[str, ...]:
    if not _SKILLS.is_dir():
        return ()
    return tuple(sorted(path.name for path in _SKILLS.iterdir() if (path / _SKILL_FILE).is_file()))


def skill_names() -> list[str]:
    """Every shipped skill (the folder names under ``skills/``), sorted."""
    return list(_names())


@cache
def _files(name: str) -> tuple[tuple[str, bytes], ...]:
    if name not in _names():
        raise KeyError(name)
    folder = _SKILLS / name
    found = [
        (path.relative_to(folder).as_posix(), path.read_bytes())
        for path in folder.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(folder).parts
    ]
    return tuple(sorted(found))


def skill_files(name: str) -> dict[str, bytes]:
    """The files of a skill: relative path (``SKILL.md``, ``references/report-template.md``) to its exact bytes.

    Raises :class:`KeyError` for an unknown name. The mapping is a fresh copy, so a caller may change it."""
    return dict(_files(name))


def _language(language: str | None) -> str:
    tag = (language or "").strip().replace("_", "-").lower()
    if tag in _LANGUAGE_BY_TAG:
        return _LANGUAGE_BY_TAG[tag]
    return _LANGUAGE_BY_TAG.get(tag.split("-", 1)[0], _FALLBACK)


def skill_for(family: str, language: str | None) -> str:
    """The name of a family's skill in a language, falling back to English for a language without one.

    ``pt-BR``, ``pt-br`` and ``pt`` all give the Brazilian Portuguese skill; a regional tag uses its base
    language (``de-AT`` gives ``de``). Raises :class:`KeyError` for an unknown family."""
    if family not in SKILL_FAMILIES:
        raise KeyError(family)
    return skill_name(family, _language(language))


def _scalar(raw: str, line: int) -> str:
    """A one-line scalar: double- or single-quoted without escapes, or plain without YAML syntax."""
    if raw[:1] in ('"', "'"):
        quote = raw[0]
        if len(raw) < 2 or not raw.endswith(quote) or quote in raw[1:-1] or "\\" in raw[1:-1]:
            raise ValueError(f"line {line}: a quoted value must be closed and hold no quotes or escapes")
        return raw[1:-1]
    if raw[:1] in tuple("&*!|>{[@`%#,?-") or ": " in raw or " #" in raw or raw.endswith(":"):
        raise ValueError(f"line {line}: only plain one-line values are read; quote this value")
    return raw


def split_front_matter(text: str) -> tuple[FrontMatter, str]:
    """The front matter and the body of a ``SKILL.md``; :class:`ValueError` for anything this reader refuses.

    The reader is deliberately small: ``key: value`` lines at the top level, a ``metadata:`` line followed by
    ``key: value`` lines indented by two spaces, one-line scalars, no comments, anchors, tags, flow collections,
    block scalars or repeated keys."""
    lines = text.split("\n")
    if lines[0] != "---":
        raise ValueError("SKILL.md must start with a '---' line")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("the front matter is not closed by a '---' line") from None
    fields: FrontMatter = {}
    mapping: dict[str, str] | None = None
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            raise ValueError(f"line {number}: empty lines are not read in the front matter")
        nested = line.startswith("  ")
        match = _KEY.match(line[2:] if nested else line)
        if match is None or line.rstrip() != line:
            raise ValueError(f"line {number}: expected 'key: value'")
        key, raw = match.group(1), match.group(2)
        if nested:
            if mapping is None:
                raise ValueError(f"line {number}: an indented line must follow a mapping key")
            if key in mapping:
                raise ValueError(f"line {number}: {key!r} is repeated")
            if raw is None:
                raise ValueError(f"line {number}: only one level of nesting is read")
            mapping[key] = _scalar(raw, number)
            continue
        if key in fields:
            raise ValueError(f"line {number}: {key!r} is repeated")
        if raw is None:
            mapping = {}
            fields[key] = mapping
        else:
            mapping = None
            fields[key] = _scalar(raw, number)
    return fields, "\n".join(lines[end + 1 :])


def _skill_problems(name: str) -> list[str]:
    problems: list[str] = []
    if len(name) > 64 or not _NAME.match(name):
        problems.append(f"{name}: the folder name is not a valid skill name")
    files = skill_files(name)
    strange = sorted(
        path
        for path in files
        if path != _SKILL_FILE
        and not (path.startswith("references/") and path.count("/") == 1 and path.endswith(".md"))
    )
    if strange:
        problems.append(f"{name}: files outside SKILL.md and references/*.md: {', '.join(strange)}")
    for path, data in files.items():
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{name}: {path} is not UTF-8 text")
    try:
        fields, body = split_front_matter(files[_SKILL_FILE].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return [*problems, f"{name}: the front matter cannot be read: {exc}"]
    unknown = sorted(set(fields) - _KNOWN_KEYS)
    if unknown:
        problems.append(f"{name}: front matter keys outside the specification: {', '.join(unknown)}")
    if fields.get("name") != name:
        problems.append(f"{name}: 'name' is {fields.get('name')!r}, not the folder name")
    description = fields.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        problems.append(f"{name}: 'description' must be 1-1024 characters")
    if fields.get("license") != SKILL_LICENSE:
        problems.append(f"{name}: 'license' must be {SKILL_LICENSE}")
    metadata = fields.get("metadata")
    if not isinstance(metadata, dict):
        problems.append(f"{name}: 'metadata' is missing or not a mapping")
    else:
        if set(metadata) != _METADATA_KEYS:
            problems.append(f"{name}: 'metadata' must have exactly {', '.join(sorted(_METADATA_KEYS))}")
        family, language = metadata.get("family", ""), metadata.get("language", "")
        if family not in SKILL_FAMILIES:
            problems.append(f"{name}: unknown family {family!r}")
        if language not in SKILL_LANGUAGES:
            problems.append(f"{name}: unknown language {language!r}")
        if skill_name(family, language) != name:
            problems.append(f"{name}: family {family!r} and language {language!r} do not give this name")
        if not metadata.get("revision", "").isdigit():
            problems.append(f"{name}: 'revision' must be a whole number as a string")
    if not body.strip():
        problems.append(f"{name}: SKILL.md has no instructions")
    if body.count("\n") + 1 >= _MAX_LINES:
        problems.append(f"{name}: the instructions have {_MAX_LINES} lines or more")
    if len(body) // 4 > _MAX_TOKENS:
        problems.append(f"{name}: the instructions have more than about {_MAX_TOKENS} tokens")
    return problems


def skill_problems() -> list[str]:
    """What is wrong with the shipped skills (empty: nothing): names and folders, the front matter (name,
    description, license, metadata family and language), the size of the instructions, files outside ``SKILL.md``
    and ``references/``, and that every family exists in every language."""
    problems: list[str] = []
    present = set(skill_names())
    if _SKILLS.is_dir():
        empty = sorted(
            path.name for path in _SKILLS.iterdir() if path.name not in present and path.name != "__pycache__"
        )
        problems += [f"{entry}: not a skill folder with a SKILL.md" for entry in empty]
    for family in SKILL_FAMILIES:
        for language in SKILL_LANGUAGES:
            if skill_name(family, language) not in present:
                problems.append(f"{skill_name(family, language)}: missing")
    for name in sorted(present):
        problems += _skill_problems(name)
    return problems
