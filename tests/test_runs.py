"""Every example in every language on the runtime: pre-check, provider settings and a complete run.

The agents answer from :class:`nodestro_runtime.testing.AnswerAllClient` (nothing is paid, no key
is needed); the runs go through the same engine, pre-check and Orkexa agents as in the studio.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from nodestro_runtime.catalog import models
from nodestro_runtime.preflight import PROVIDER_CHECKS, preflight
from nodestro_runtime.providers import provider_of, qualify
from nodestro_runtime.schemas import LANGUAGES, RunIn, SettingsIn, Workflow
from nodestro_runtime.testing import AnswerAllClient
from nodestro_runtime.workspace import Workspace
import pytest

import nodestro_examples as library
from nodestro_examples import samples

IDS = library.template_ids()


def copy(workspace: Workspace, template_id: str, language: str) -> Workflow:
    """A template as an ordinary saved workflow, its parts saved first (like the gallery's copy)."""
    sensitive = library.structure(template_id).sensitive
    parts: dict[str, tuple[str, int | None]] = {}
    for part_id in library.part_ids(template_id):
        child = workspace.save_workflow(library.build_part(part_id, language, sensitive=sensitive))
        parts[part_id] = (child.id, workspace.current_version(child))
    return workspace.save_workflow(library.link_parts(library.build(template_id, language), parts))


@pytest.fixture
def workspace(tmp_path: Path) -> Iterator[Workspace]:
    fake = AnswerAllClient()
    found = Workspace(tmp_path / "data", client_factory=lambda _provider: fake, integrations=[])
    found.fake = fake  # type: ignore[attr-defined]
    yield found
    found.close()


def _start_input(workflow: Workflow) -> RunIn:
    start = next(node for node in workflow.nodes if node.type == "start")
    assert start.start is not None
    values: dict[str, Any] = {}
    if start.start.fields:
        for field in start.start.fields:
            if field.type == "file":
                continue
            if field.default not in (None, "", []):
                values[field.name] = field.default
            elif field.required:
                values[field.name] = field.options[0] if field.options else "Beispiel"
    return RunIn(input=start.start.default_input or "", values=values)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("template_id", IDS)
async def test_every_example_runs_in_every_language(workspace: Workspace, template_id: str, language: str) -> None:
    workflow = copy(workspace, template_id, language)
    check = preflight(workspace, workflow)
    # The fake client stands in for the provider; the key check is the next test's subject.
    errors = [problem for problem in check.problems if problem.level == "error" and problem.code not in PROVIDER_CHECKS]
    assert not errors, (template_id, language, errors)
    assert all(not issues for issues in check.agents.values()), (template_id, language, check.agents)
    run = await workspace.run(workflow, _start_input(workflow))
    done = await workspace.wait(run.id, timeout=60)
    # Approvals wait for a person; the test approves every one (sub-workflows included).
    for _ in range(10):
        if done.status != "paused":
            break
        for item in [*workspace.runs.live_runs(), done]:
            for node_id, state in item.nodes.items():
                if state.status == "awaiting_approval":
                    workspace.decide(item.id, node_id, "approved", "ok")
        done = await workspace.wait(run.id, timeout=60)
    assert done.status == "succeeded", (template_id, language, done.error, done.error_code)
    assert done.output is not None
    succeeded = [node_id for node_id, state in done.nodes.items() if state.status == "succeeded"]
    agents = [node.id for node in workflow.nodes if node.type == "agent"]
    assert set(agents) & set(succeeded), (template_id, language)


@pytest.mark.parametrize("template_id", IDS)
def test_examples_need_exactly_the_providers_they_name(tmp_path: Path, template_id: str) -> None:
    """Without settings the pre-check names the missing key; with the provider's key nothing is missing."""
    known = {info.id for info in models()}
    workspace = Workspace(tmp_path / "data", integrations=[])
    try:
        workflow = copy(workspace, template_id, "en")
        wanted = {provider_of(node.agent.model) for node in workflow.nodes if node.agent is not None} | {"anthropic"}
        assert all(qualify(node.agent.model) in known for node in workflow.nodes if node.agent is not None)
        missing = {problem.code for problem in preflight(workspace, workflow).problems if problem.level != "info"}
        assert missing == {"check.api_key_missing"}, (template_id, missing)
        workspace.update_settings(
            SettingsIn.model_validate({"providers": {name: {"api_key": f"test-{name}"} for name in wanted}})
        )
        remaining = [problem for problem in preflight(workspace, workflow).problems if problem.level == "error"]
        assert not remaining, (template_id, remaining)
    finally:
        workspace.close()


@pytest.mark.parametrize("language", LANGUAGES)
def test_test_cases_and_their_sample_files_belong_to_the_copy(workspace: Workspace, language: str) -> None:
    """The prepared test cases of every template become cases of the copy, sample files stored as inputs."""
    with_tests = [template_id for template_id in IDS if library.structure(template_id).tests]
    assert with_tests
    stored: list[str] = []

    def store(name: str, media_type: str, data: bytes) -> str:
        entry = workspace.inputs.add(data, name=name, media_type=media_type, origin="test")
        stored.append(entry.id)
        return entry.id

    for template_id in with_tests:
        workflow = copy(workspace, template_id, language)

        cases = samples.suite_cases(template_id, language, workflow, store)
        assert cases, (template_id, language)
        assert all(case["name"] for case in cases)
        for file_id in stored:
            assert workspace.inputs.get(file_id) is not None
