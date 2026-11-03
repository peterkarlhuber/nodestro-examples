"""A model per agent: every agent's task profile, the agent plan and the per-agent models of a copy (EX-011).

Library functions only: no workspace, no run and no model call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nodestro_runtime.local_models import TASKS
from nodestro_runtime.schemas import LANGUAGES, WorkflowIn
from pydantic import ValidationError
import pytest

import nodestro_examples as library

IDS = library.template_ids()

#: The task of every agent, reviewed one by one (key -> task); a change here is a deliberate decision.
EXPECTED: dict[str, dict[str, str]] = {
    "blog-article": {"brief": "write", "writer": "write", "editor": "tool_agent"},
    "business-idea": {
        "coach": "orchestrator",
        "jury": "analysis",
        "idea-market/expert": "analysis",
        "idea-economics/expert": "tool_agent",
        "idea-risks/expert": "analysis",
        "idea-regulation/expert": "analysis",
        "idea-operations/expert": "analysis",
    },
    "citizen-inquiry": {"triage": "document_vision", "rules": "tool_agent", "reply": "write"},
    "club-event": {"schedule": "tool_agent", "budget": "tool_agent", "communication": "write", "board_paper": "write"},
    "code-review": {"bugs": "coding", "security": "coding", "fix": "coding"},
    "construction-delay": {
        "schedule": "tool_agent",
        "control": "orchestrator",
        "report": "write",
        "construction-site/expert": "analysis",
        "construction-supply/expert": "analysis",
        "construction-claims/expert": "analysis",
        "construction-recovery/expert": "tool_agent",
    },
    "contract-review": {
        "structure": "extract",
        "explain": "write",
        "checkpoints": "tool_agent",
        "report": "extract",
        "critical": "analysis",
    },
    "creator-strategy": {"strategy": "document_vision", "ideas": "tool_agent", "calendar": "write"},
    "customer-service": {"triage": "classify", "policy": "tool_agent", "reply": "write", "deescalation": "write"},
    "farm-planning": {"rotation": "analysis", "margins": "tool_agent", "review": "judge"},
    "financial-analysis": {"research": "extract", "analysis": "analysis", "review": "judge"},
    "household-budget": {"budget": "tool_agent", "savings": "tool_agent", "check": "judge"},
    "hr-recruiting": {
        "profile": "write",
        "job_ad": "write",
        "interview": "write",
        "fairness": "judge",
        "revise": "write",
    },
    "learning-plan": {"assessment": "tool_agent", "plan": "tool_agent", "tutor": "write", "quiz": "write"},
    "nonprofit-campaign": {"campaign": "write", "impact": "tool_agent", "integrity": "judge"},
    "production-downtime": {
        "downtime": "tool_agent",
        "causes": "analysis",
        "measures": "write",
        "quality-check/risk": "analysis",
        "quality-check/plan": "write",
    },
    "quality-8d": {
        "problem": "document_vision",
        "root_cause": "tool_agent",
        "actions": "write",
        "report": "extract",
        "containment": "write",
    },
    "real-estate": {"returns": "tool_agent", "property": "document_vision", "assessment": "analysis"},
    "research-hypotheses": {
        "framing": "extract",
        "coordinator": "orchestrator",
        "design": "analysis",
        "research-hypothesis-team/expert": "analysis",
        "research-statistics/expert": "analysis",
        "research-qualitative/expert": "analysis",
        "research-ethics/expert": "analysis",
    },
    "restaurant-menu": {"concept": "write", "costing": "tool_agent", "menu": "write"},
    "sales-offer": {"needs": "extract", "solution": "tool_agent", "offer": "tool_agent"},
    "sme-swot": {"internal": "analysis", "external": "analysis", "strategy": "analysis", "critic": "judge"},
    "supplier-comparison": {"cost": "tool_agent", "risk": "tool_agent", "recommendation": "analysis"},
    "travel-plan": {"itinerary": "write", "budget": "tool_agent", "organizer": "write", "documents": "write"},
}


def _plans() -> list[tuple[str, library.AgentPlan]]:
    return [(template_id, plan) for template_id in IDS for plan in library.agent_plan(template_id)]


def _spec_nodes() -> list[tuple[str, library.NodeSpec]]:
    found = [(template_id, node) for template_id in IDS for node in library.structure(template_id).nodes]
    parts = {part_id for template_id in IDS for part_id in library.part_ids(template_id)}
    found += [(part_id, node) for part_id in sorted(parts) for node in library.part(part_id).nodes]
    return found


# ---- the task of every agent --------------------------------------------------------------


def test_every_agent_names_a_task_that_fits_its_tier() -> None:
    agents = [(owner, node) for owner, node in _spec_nodes() if node.type in ("agent", "orchestrator")]
    assert len(agents) == 97
    for owner, node in agents:
        assert node.task in library.AGENT_TASKS, (owner, node.id)
        assert library.tier_fits(node.tier, node.task), (owner, node.id, node.tier, node.task)
    for owner, node in _spec_nodes():
        if node.type not in ("agent", "orchestrator"):
            assert node.task is None, (owner, node.id)


def test_the_reviewed_tasks_are_the_ones_the_templates_name() -> None:
    assert set(EXPECTED) == set(IDS)
    for template_id in IDS:
        assert {plan.key: plan.task for plan in library.agent_plan(template_id)} == EXPECTED[template_id], template_id


def test_tool_users_have_a_model_that_can_call_tools() -> None:
    for template_id, plan in _plans():
        if not plan.tools:
            continue
        assert "tools" in plan.needs, (template_id, plan.key)
        # Tool work has a task that needs tools; only a demanding analysis keeps its own profile (its rank), and
        # its plan needs tools anyway.
        assert "tools" in TASKS[plan.task].needs or plan.task == "analysis", (template_id, plan.key)
    # Knowledge search, memory, integrations and delegation count as tools.
    plans = {(template_id, plan.key): plan for template_id, plan in _plans()}
    for key in [
        ("citizen-inquiry", "rules"),
        ("learning-plan", "plan"),
        ("customer-service", "policy"),
        ("business-idea", "coach"),
        ("code-review", "bugs"),
    ]:
        assert plans[key].tools, key
    assert not plans[("hr-recruiting", "profile")].tools


def test_agents_that_read_images_have_a_model_with_vision() -> None:
    readers = {}
    for template_id, plan in _plans():
        if plan.vision:
            readers[(template_id, plan.key)] = plan.task
            assert plan.files and "vision" in plan.needs, (template_id, plan.key)
            # Reading the documents is the work, unless the agent works with tools on them.
            assert plan.task == ("tool_agent" if plan.tools else "document_vision"), (template_id, plan.key)
        else:
            assert plan.task != "document_vision" and "vision" not in plan.needs, (template_id, plan.key)
    assert readers == {
        ("citizen-inquiry", "triage"): "document_vision",
        ("citizen-inquiry", "rules"): "tool_agent",
        ("construction-delay", "schedule"): "tool_agent",
        ("creator-strategy", "strategy"): "document_vision",
        ("quality-8d", "problem"): "document_vision",
        ("quality-8d", "root_cause"): "tool_agent",
        ("real-estate", "returns"): "tool_agent",
        ("real-estate", "property"): "document_vision",
    }


def test_orchestrators_coding_agents_and_routers() -> None:
    for template_id, plan in _plans():
        assert (plan.kind == "orchestrator") == (plan.task == "orchestrator"), (template_id, plan.key)
    plans = {(template_id, plan.key): plan for template_id, plan in _plans()}
    assert {key for key, plan in plans.items() if plan.task == "coding"} == {
        ("code-review", "bugs"),
        ("code-review", "security"),
        ("code-review", "fix"),
    }
    # The agent that routes enquiries to the escalation branch is a small classifier.
    assert plans[("customer-service", "triage")].task == "classify"
    assert plans[("customer-service", "triage")].tier == "fast"


def test_the_tier_rule() -> None:
    # Capable tasks never run on the fast tier; only tasks with a strong ideal use the strong tier.
    assert library.tier_fits("fast", "classify") and not library.tier_fits("strong", "classify")
    assert library.tier_fits(None, "classify") and library.tier_fits("standard", "judge")
    for task in ("analysis", "coding", "judge", "orchestrator"):
        assert not library.tier_fits("fast", task), task
    for task in ("analysis", "coding", "orchestrator"):
        assert library.tier_fits("strong", task), task
    for task in ("extract", "write", "document_vision", "tool_agent", "judge"):
        assert library.tier_fits("fast", task) != (task == "judge"), task
        assert not library.tier_fits("strong", task), task
    assert "embedding" not in library.AGENT_TASKS and "assistant" not in library.AGENT_TASKS


def _template(name: str = "travel-plan") -> dict[str, Any]:
    data: dict[str, Any] = json.loads((Path(library.__file__).parent / "templates" / f"{name}.json").read_text("utf-8"))
    return data


def _node(data: dict[str, Any], node_id: str) -> dict[str, Any]:
    node: dict[str, Any] = next(item for item in data["nodes"] if item["id"] == node_id)
    return node


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: _node(data, "itinerary").update(task="dreaming"), "unknown task 'dreaming'"),
        (lambda data: _node(data, "itinerary").update(task="assistant"), "unknown task 'assistant'"),
        (lambda data: _node(data, "itinerary").update(task="orchestrator"), "belongs to orchestrators"),
        (lambda data: _node(data, "itinerary").update(tier="fast", task="analysis"), "tier fast does not fit"),
        (lambda data: _node(data, "itinerary").update(tier="strong", task="classify"), "tier strong does not fit"),
        (lambda data: _node(data, "start").update(task="write"), "has a task but is no agent"),
    ],
)
def test_invalid_tasks_are_refused_on_load(change: Any, message: str) -> None:
    data = _template()
    change(data)
    with pytest.raises(ValidationError, match=message):
        library.TemplateSpec.model_validate(data)


def test_an_orchestrator_needs_the_orchestrator_task() -> None:
    data = _template("business-idea")
    _node(data, "coach")["task"] = "analysis"
    with pytest.raises(ValidationError, match="belongs to orchestrators"):
        library.TemplateSpec.model_validate(data)


# ---- the agent plan -----------------------------------------------------------------------


def test_the_plan_names_every_agent_a_copy_creates() -> None:
    for template_id in IDS:
        plans = library.agent_plan(template_id)
        keys = [plan.key for plan in plans]
        assert len(set(keys)) == len(keys), template_id
        expected = [node.id for node in library.build(template_id, "en").nodes if node.agent or node.orchestrator] + [
            f"{part_id}/{node.id}"
            for part_id in library.part_ids(template_id)
            for node in library.build_part(part_id, "en").nodes
            if node.agent or node.orchestrator
        ]
        assert keys == expected, template_id
        for plan in plans:
            assert plan.key == library.agent_key(plan.node_id, plan.part)
            assert plan.key == (f"{plan.part}/{plan.node_id}" if plan.part else plan.node_id)
            assert set(TASKS[plan.task].needs) <= set(plan.needs)


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_plan_names_agents_in_the_language(language: str) -> None:
    for template_id in IDS:
        workflow = library.build(template_id, language)
        labels = {node.id: node.label for node in workflow.nodes}
        parts = {part_id: library.build_part(part_id, language) for part_id in library.part_ids(template_id)}
        for plan in library.agent_plan(template_id, language):
            nodes = labels if plan.part is None else {node.id: node.label for node in parts[plan.part].nodes}
            assert plan.name == nodes[plan.node_id], (template_id, plan.key)


def test_the_plan_describes_the_agents() -> None:
    plans = {plan.key: plan for plan in library.agent_plan("construction-delay")}
    schedule = plans["schedule"]
    assert (schedule.tier, schedule.tools, schedule.structured, schedule.files, schedule.vision, schedule.judge) == (
        "standard",
        True,
        True,
        True,
        True,
        False,
    )
    assert schedule.needs == ["completion", "tools", "vision"]
    assert plans["control"].kind == "orchestrator" and plans["control"].needs == ["completion", "tools"]
    assert plans["construction-claims/expert"].part == "construction-claims"
    blog = {plan.key: plan for plan in library.agent_plan("blog-article")}
    assert blog["writer"].judge and blog["brief"].tier == "fast" and not blog["brief"].files
    assert library.agent_plan("financial-analysis")[1].tier == "strong"


# ---- models per agent ---------------------------------------------------------------------


def test_model_choice_stays_compatible() -> None:
    plain = library.model_choice("ollama:qwen3.5:9b")
    assert (plain.fast, plain.standard, plain.strong, plain.agents, plain.judge) == (
        "ollama:qwen3.5:9b",
        "ollama:qwen3.5:9b",
        "ollama:qwen3.5:9b",
        {},
        None,
    )
    assert plain.judge_model() == "ollama:qwen3.5:9b"
    chosen = library.model_choice("ollama:qwen3.5:9b", agents={"triage": "ollama:qwen3.5:4b"}, judge="ollama:x:1")
    assert chosen.agents == {"triage": "ollama:qwen3.5:4b"} and chosen.judge_model() == "ollama:x:1"
    assert chosen.for_agent("triage", "fast") == "ollama:qwen3.5:4b"
    assert chosen.for_agent("reply", None) == "ollama:qwen3.5:9b"
    assert library.model_choice(agents={"a": "ollama:m:1"}).standard == library.DEFAULT_MODELS["standard"]


def _models(workflow: WorkflowIn) -> dict[str, str]:
    found = {node.id: node.agent.model for node in workflow.nodes if node.agent is not None}
    found.update({node.id: node.orchestrator.model for node in workflow.nodes if node.orchestrator is not None})
    return found


def test_agents_get_their_own_model_and_the_rest_keeps_the_tier() -> None:
    models = library.model_choice(
        "ollama:qwen3.5:9b",
        agents={"coach": "ollama:qwen3.6:35b-a3b", "idea-economics/expert": "ollama:qwen3.5:4b"},
        judge="ollama:ministral-3:14b",
    )
    workflow = library.build("business-idea", "en", models=models)
    assert _models(workflow) == {"coach": "ollama:qwen3.6:35b-a3b", "jury": "ollama:qwen3.5:9b"}
    economics = library.build_part("idea-economics", "en", models=models)
    market = library.build_part("idea-market", "en", models=models)
    assert set(_models(economics).values()) == {"ollama:qwen3.5:4b"}
    assert set(_models(market).values()) == {"ollama:qwen3.5:9b"}
    # The key of a part's agent never applies to the template's node of the same id, nor the other way round.
    shadow = library.model_choice("ollama:qwen3.5:9b", agents={"expert": "ollama:qwen3.5:4b"})
    assert set(_models(library.build_part("idea-market", "en", models=shadow)).values()) == {"ollama:qwen3.5:9b"}
    blog = library.build("blog-article", "en", models=models)
    writer = next(node.agent for node in blog.nodes if node.id == "writer")
    assert writer is not None and writer.quality.judge_model == "ollama:ministral-3:14b"


def test_with_anthropic_an_agent_model_replaces_only_that_agent() -> None:
    models = library.model_choice(agents={"bugs": "ollama:devstral-small-2:24b"})
    built = _models(library.build("code-review", "en", models=models))
    assert built == {
        "bugs": "ollama:devstral-small-2:24b",
        "security": library.DEFAULT_MODELS["standard"],
        "fix": library.DEFAULT_MODELS["standard"],
    }


class _Host:
    def __init__(self) -> None:
        self.saved: list[WorkflowIn] = []

    def save_workflow(self, workflow: WorkflowIn) -> tuple[str, int | None]:
        self.saved.append(workflow)
        return f"wf_{len(self.saved)}", 1

    def add_knowledge(self, data: bytes, *, name: str, media_type: str, description: str, collection: str) -> str:
        return f"kf_{name}"


def test_a_copy_takes_the_models_per_agent() -> None:
    plans = library.agent_plan("construction-delay")
    agents = {plan.key: f"ollama:model-{index}:1" for index, plan in enumerate(plans)}
    host = _Host()
    made = library.instantiate("construction-delay", "de", host, models=library.model_choice(agents=agents))
    found = _models(made.workflow)
    for saved, part_id in zip(host.saved, library.part_ids("construction-delay"), strict=True):
        found.update({f"{part_id}/{key}": model for key, model in _models(saved).items()})
    assert found == agents


def test_a_copy_refuses_models_for_unknown_agents() -> None:
    host = _Host()
    with pytest.raises(KeyError, match="ghost"):
        library.instantiate("blog-article", "en", host, models=library.model_choice(agents={"ghost": "ollama:m:1"}))
    # A key of another template's part is unknown here too; nothing was saved.
    with pytest.raises(KeyError, match="idea-market/expert"):
        library.instantiate(
            "travel-plan", "en", host, models=library.model_choice(agents={"idea-market/expert": "ollama:m:1"})
        )
    assert host.saved == []


def test_the_gallery_shows_the_task() -> None:
    detail = library.detail("code-review", "en")
    assert {agent.node_id: agent.task for agent in detail.agent_details} == {
        "bugs": "coding",
        "security": "coding",
        "fix": "coding",
    }
