"""The shipped agent templates (NAL-B1): valid in every language, built like the agents of the examples."""

from __future__ import annotations

import json
from typing import Any

from nodestro_runtime.engine import check_workflow
from nodestro_runtime.schemas import LANGUAGES, AgentConfig, TemplateMeta, Workflow
from pydantic import ValidationError
import pytest

import nodestro_examples as library
from nodestro_examples import agents

IDS = agents.agent_ids()


def test_the_first_five_templates_ship() -> None:
    assert IDS == ("web-research", "summary", "document-analysis", "text-editing", "data-analysis")
    assert {agents.agent_structure(agent_id).category for agent_id in IDS} == set(agents.AGENT_CATEGORIES)


def test_the_templates_have_no_problems() -> None:
    assert agents.agent_problems() == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_template_builds_in_every_language(language: str) -> None:
    for agent_id in IDS:
        agent, meta = agents.build_agent(agent_id, language)
        AgentConfig.model_validate(agent.model_dump())
        TemplateMeta.model_validate(meta.model_dump())
        assert meta.locale == language and meta.origin == agents.agent_origin(agent_id)
        assert meta.summary and meta.examples and meta.tests
        # The common rules of the examples are part of the system prompt.
        assert library.common(language).answer in agent.system_prompt
        # Placed into a workflow, it is valid for the engine.
        workflow = Workflow.model_validate(
            {
                "name": agent.name,
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "a", "type": "agent", "agent": agent.model_dump()},
                    {"id": "out", "type": "output"},
                ],
                "edges": [{"id": "e1", "source": "start", "target": "a"}, {"id": "e2", "source": "a", "target": "out"}],
            }
        )
        assert not check_workflow(workflow), (language, agent_id)


def test_the_web_research_template_is_the_example_agent() -> None:
    """One prompt in one place: the template takes the example's agent with its texts and tool limits."""
    agent, meta = agents.build_agent("web-research", "en", services={"search": "conn_1"})
    example = library.build("web-research", "en", services={"search": "conn_1"})
    [original] = [node.agent for node in example.nodes if node.id == "research"]
    assert original is not None
    assert agent.model_dump(exclude={"task"}) == original.model_dump(exclude={"task"})
    assert agent.task == "tool_agent"
    assert meta.requirements.services == ["search"] and not meta.requirements.offline_capable
    assert meta.requirements.capabilities == ["tools", "structured_output"]


def test_requirements_follow_the_agent() -> None:
    _, summary = agents.build_agent("summary", "de")
    assert summary.requirements.tools == [] and summary.requirements.offline_capable
    assert summary.requirements.min_tier == "fast"
    _, data = agents.build_agent("data-analysis", "de")
    assert data.requirements.tools == ["table_totals", "calculator"] and data.requirements.services == []


def test_models_and_versions() -> None:
    models = library.ModelChoice(fast="ollama:qwen3:4b", standard="ollama:qwen3:8b", strong="ollama:qwen3:14b")
    agent, _ = agents.build_agent("summary", "en", models=models)
    assert agent.model == "ollama:qwen3:4b"
    assert agents.agent_version("summary") == f"{library.__version__}+r1"
    TemplateMeta(origin=agents.agent_origin("summary"))  # matches the runtime's origin pattern


def test_builds_are_fresh_objects() -> None:
    first, _ = agents.build_agent("summary", "en")
    first.system_prompt = "changed"
    second, _ = agents.build_agent("summary", "en")
    assert second.system_prompt != "changed"


def test_unknown_ids_and_languages() -> None:
    with pytest.raises(KeyError):
        agents.agent_structure("nope")
    with pytest.raises(KeyError):
        agents.agent_structure("../templates/web-research")
    with pytest.raises(KeyError):
        agents.agent_texts("nope", "en")
    agent, meta = agents.build_agent("summary", "xx")
    assert meta.locale == library.FALLBACK_LANGUAGE and agent.name == "Summariser"


def _spec(agent_id: str) -> dict[str, Any]:
    return json.loads((library._ROOT / "agents" / f"{agent_id}.json").read_text("utf-8"))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.pop("agent"), "either its own agent"),
        (lambda data: data.update(example={"template": "web-research", "node": "research"}), "either its own agent"),
        (lambda data: data["agent"].update(type="output"), "is an agent node"),
        (lambda data: data.update(category="sports"), "category"),
        (lambda data: data.update(unknown=1), "unknown"),
    ],
)
def test_invalid_templates_are_refused_on_load(change: Any, message: str) -> None:
    data = _spec("summary")
    change(data)
    with pytest.raises(ValidationError, match=message):
        agents.AgentSpec.model_validate(data)


def test_problems_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = agents.agent_structure("data-analysis")
    assert spec.agent is not None
    broken = spec.model_copy(
        update={"agent": spec.agent.model_copy(update={"tier": "fast", "task": "analysis", "tools": ["teleport"]})}
    )
    original = agents.agent_structure
    monkeypatch.setattr(
        agents, "agent_structure", lambda agent_id: broken if agent_id == "data-analysis" else original(agent_id)
    )
    found = agents.agent_problems()
    assert any("tier fast does not fit task analysis" in item for item in found)
    assert any("unknown tools teleport" in item for item in found)


def test_french_texts_use_typographic_apostrophes() -> None:
    for agent_id in IDS:
        raw = (library._ROOT / "texts" / "fr" / "agents" / f"{agent_id}.json").read_text("utf-8")
        assert "'" not in raw, agent_id
