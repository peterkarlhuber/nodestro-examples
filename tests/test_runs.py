"""Every example in every language on the runtime: pre-check, provider settings and a complete run.

The agents answer from a deterministic double (nothing is paid, no key is needed); the runs go
through the same engine, pre-check and Orkexa agents as in the studio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import Scenario, copy, finish, start_request
from nodestro_runtime.catalog import models
from nodestro_runtime.graph import data_sources
from nodestro_runtime.preflight import PROVIDER_CHECKS, preflight
from nodestro_runtime.providers import provider_of, qualify
from nodestro_runtime.schemas import LANGUAGES, SettingsIn
from nodestro_runtime.workspace import Workspace
import pytest

import nodestro_examples as library
from nodestro_examples import samples

IDS = library.template_ids()


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("template_id", IDS)
async def test_every_example_runs_in_every_language(make_workspace: Any, template_id: str, language: str) -> None:
    scenario = Scenario()
    workspace = make_workspace(scenario)
    workflow = copy(workspace, template_id, language)
    check = preflight(workspace, workflow)
    # The double stands in for the provider; the key check is the next test's subject.
    errors = [problem for problem in check.problems if problem.level == "error" and problem.code not in PROVIDER_CHECKS]
    assert not errors, (template_id, language, errors)
    assert all(not issues for issues in check.agents.values()), (template_id, language, check.agents)
    run = await workspace.run(workflow, start_request(workflow))
    done = await finish(workspace, run)
    assert done.status == "succeeded", (template_id, language, done.error, done.error_code)
    assert done.output is not None
    succeeded = [node_id for node_id, state in done.nodes.items() if state.status == "succeeded"]
    agents = [node.id for node in workflow.nodes if node.type == "agent"]
    assert set(agents) & set(succeeded), (template_id, language)
    for node_id in agents:
        prompt = done.nodes[node_id].prompt or ""
        # Every placeholder is filled and nothing arrives as an unplanned appendix.
        assert "{{" not in prompt and "# Eingaben" not in prompt, (template_id, language, node_id, prompt)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("template_id", [item for item in IDS if library.structure(item).samples])
async def test_agents_reading_the_input_keep_the_text_when_files_are_attached(
    make_workspace: Any, template_id: str, language: str
) -> None:
    """With a file in the form the start node's result names the files only: the text must still arrive.

    The prepared text holds what the files do not (target values, cost rates, the request itself).
    """
    workspace = make_workspace()
    workflow = copy(workspace, template_id, language)
    request = start_request(workflow)
    sample = library.structure(template_id).samples[0]
    name, media_type, data = samples.render(template_id, sample.id, language)
    stored = workspace.inputs.add(data, name=name, media_type=media_type, origin="test")
    request.values[sample.field] = [stored.id]
    done = await finish(workspace, await workspace.run(workflow, request))
    assert done.status == "succeeded", (template_id, language, done.error)
    marker = request.input.splitlines()[0]
    for node in workflow.nodes:
        if node.agent is None or "start" not in data_sources(workflow, node.id):
            continue
        state = done.nodes[node.id]
        assert marker in (state.prompt or ""), (template_id, language, node.id, state.prompt)
        assert name in [item.name for item in state.files], (template_id, language, node.id)


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
