"""The web-research example (NAL-B2) on the runtime, with the deterministic test search provider and served pages.

Nothing here reaches the internet or a paid service: searches use the runtime's test provider with the evaluation
set's fixtures (``evaluation/web-research.json``), pages come from a mock transport, and every outbound connection
or name lookup fails the test. The agent is a scripted model that replays each question's reference script; what
the engine, the web tools and the source ledger make of it is real. These tests prove the mechanics (limits, source
checks, filled sources, refused addresses, pre-checks), not the quality of a real model's research.
"""

from __future__ import annotations

import functools
import socket
from types import SimpleNamespace
from typing import Any

from conftest import Scenario, finish, instantiate
import httpx
from nodestro_runtime import web_tools
from nodestro_runtime.conditions import parse_result
from nodestro_runtime.local_service import InstalledModel
from nodestro_runtime.preflight import preflight
from nodestro_runtime.schemas import LANGUAGES, RunIn, SettingsIn
from nodestro_runtime.workspace import Workspace
import orkexa.web
import pytest

import nodestro_examples as library

TEMPLATE = "web-research"
EVALUATION = library.evaluation_set(TEMPLATE)
RESEARCHERS = ("research", "research_thorough")
#: The test cases of spec NAL-B2 point 9 that a scripted run can show (the rest are pre-check tests below).
KINDS = {
    "simple",
    "multi_step",
    "ambiguous",
    "source_language",
    "provider_unavailable",
    "empty_results",
    "contradiction",
    "prompt_injection",
    "invalid_url",
    "network_failure",
    "call_limit",
    "foreign_source",
}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Every test here fails on a real outbound connection or name lookup (loopback is allowed for the store)."""
    attempts: list[Any] = []
    original = socket.socket.connect

    def connect(self: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
            attempts.append(address)
            raise AssertionError(f"network access in a test: {address}")
        return original(self, address)

    def lookup(host: Any, *args: Any, **kwargs: Any) -> Any:
        attempts.append(host)
        raise AssertionError(f"name lookup in a test: {host}")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    return attempts


class Web:
    """The test provider with the evaluation set's hits and the pages served instead of the web."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, provider_down: bool = False) -> None:
        self.requested: list[str] = []
        fixtures = {query: [hit.model_dump() for hit in hits] for query, hits in EVALUATION.searches.items()}
        self.provider = orkexa.web.TestSearchProvider(fixtures, generate=False)
        info = web_tools.PROVIDERS["test"]

        def build(_connection: Any) -> Any:
            if provider_down:
                return SimpleNamespace(search=self._unavailable)
            return self.provider

        monkeypatch.setitem(
            web_tools.PROVIDERS, "test", web_tools.SearchProviderInfo("test", build, price_usd=info.price_usd)
        )
        transport = httpx.MockTransport(self._serve)
        monkeypatch.setattr(
            orkexa.web, "fetch_page", functools.partial(orkexa.web.fetch_page, mock_transport=transport)
        )

    @staticmethod
    async def _unavailable(_request: Any) -> Any:
        raise orkexa.web.SearchUnavailable("the test provider is down", provider="test")

    def _serve(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        page = EVALUATION.pages.get(url)
        if page is None:
            return httpx.Response(404, headers={"content-type": "text/plain"}, content=b"missing")
        if page.fails == "network":
            raise httpx.ConnectError("connection reset", request=request)
        return httpx.Response(page.status, headers={"content-type": page.type}, content=page.body.encode())


def _scenario(question: library.EvaluationQuestion) -> Scenario:
    """A model that replays the question's reference script (both researchers: only one of them runs)."""
    calls = [(step.tool, step.input) for step in question.script if step.tool is not None]
    answer = question.script[-1].answer
    assert answer is not None
    return Scenario(
        {node_id: dict(answer) for node_id in RESEARCHERS},
        tool_calls={node_id: list(calls) for node_id in RESEARCHERS},
    )


def _values(question: library.EvaluationQuestion) -> dict[str, Any]:
    values: dict[str, Any] = {"question": question.question, "thorough": question.thorough}
    if question.source_language:
        values["source_language"] = question.source_language
    return values


async def _run(make_workspace: Any, monkeypatch: pytest.MonkeyPatch, question: library.EvaluationQuestion) -> Any:
    web = Web(monkeypatch, provider_down=question.provider == "down")
    workspace = make_workspace(_scenario(question))
    workflow, _made = instantiate(workspace, TEMPLATE, EVALUATION.language)
    workspace.fake.learn(workflow)
    done = await finish(workspace, await workspace.run(workflow, RunIn(input="", values=_values(question))))
    return web, workflow, done


def test_the_evaluation_set_covers_the_planned_cases() -> None:
    assert {question.kind for question in EVALUATION.questions} == KINDS
    # The prompt-injection page is part of the set and asks for an internal address.
    injected = [page for page in EVALUATION.pages.values() if "IGNORE ALL PREVIOUS INSTRUCTIONS" in page.body]
    assert len(injected) == 1 and "169.254.169.254" in injected[0].body
    # Every served page is synthetic and marked as such.
    assert all("Synthetic" in page.body or page.fails for page in EVALUATION.pages.values())
    with pytest.raises(KeyError):
        library.evaluation_set("travel-plan")


@pytest.mark.parametrize("question", EVALUATION.questions, ids=lambda question: question.id)
async def test_every_question_of_the_evaluation_set(
    make_workspace: Any, monkeypatch: pytest.MonkeyPatch, _no_network: list[Any], question: library.EvaluationQuestion
) -> None:
    web, _workflow, done = await _run(make_workspace, monkeypatch, question)
    expect = question.expect
    ran = "research_thorough" if question.thorough else "research"
    skipped = "research" if question.thorough else "research_thorough"
    assert done.nodes[skipped].status == "skipped", done.nodes[skipped].status
    step = done.nodes[ran]
    if expect.status == "failed":
        assert done.status == "failed" and step.error_code == expect.error_code, (done.status, step.error_code)
    else:
        assert done.status == "succeeded", (done.error, step.error_code, step.error)
    outputs = [call.output or "" for call in step.tool_calls]
    for code in expect.tool_errors:
        assert any(code in output for output in outputs), (code, outputs)
    if not expect.tool_errors:
        assert not any(call.is_error for call in step.tool_calls), outputs
    urls = {entry.id: entry.url for entry in done.sources}
    result = done.output if done.status == "succeeded" else step.output
    for text in expect.not_in_result:
        assert text not in str(result) and text not in str(done.output)
    for url in expect.not_fetched:
        assert url not in web.requested and url not in [call.input.get("url") for call in step.tool_calls]
    if expect.search_language is not None:
        assert [request.language for request in web.provider.requests] == [expect.search_language]
    assert _no_network == []
    if done.status != "succeeded":
        return
    parsed = parse_result(done.output)
    # The structured result: the model's fields plus the two the run filled from the source ledger.
    assert set(parsed) == {"answer", "findings", "contradictions", "gaps", "retrieved", "sources"}
    assert isinstance(parsed["answer"], str) and isinstance(parsed["findings"], list)
    listed = [line.split(" · ")[0] for line in parsed["sources"]]
    cited = {urls[source] for source in listed}
    assert cited == set(expect.cited_urls), (cited, parsed["sources"])
    assert not cited & set(expect.not_cited_urls)
    # Every listed source is in the ledger with its title, address and retrieval time; nothing else is listed.
    for line in parsed["sources"]:
        entry = next(item for item in done.sources if item.id == line.split(" · ")[0])
        assert entry.url in line and entry.retrieved_at.strftime("%Y-%m-%dT%H:%M:%S") in line
    if cited:
        first = min(entry.retrieved_at for entry in done.sources if entry.url in cited)
        assert parsed["retrieved"].startswith(first.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        assert parsed["retrieved"] == "" and parsed["sources"] == []
    assert bool(parsed["contradictions"]) == expect.contradictions
    assert bool(parsed["gaps"]) or not expect.gaps
    for word in expect.mentions:
        assert word in parsed["answer"].lower()


async def test_a_model_that_follows_the_injected_instruction_is_stopped_by_the_guard(
    make_workspace: Any, monkeypatch: pytest.MonkeyPatch, _no_network: list[Any]
) -> None:
    """The injected text reaches the model only inside the marked external content; a model that obeys it anyway
    has no tool that writes, and the internal address it is sent to is refused before any connection."""
    honest = next(question for question in EVALUATION.questions if question.kind == "prompt_injection")
    target = honest.expect.not_fetched[0]
    obeying = honest.model_copy(
        update={
            "script": [
                *honest.script[:2],
                library.EvaluationStep(tool="fetch_web_page", input={"url": target}),
                library.EvaluationStep(answer={**(honest.script[-1].answer or {}), "answer": "PWNED-7731 [S1]"}),
            ]
        }
    )
    web, workflow, done = await _run(make_workspace, monkeypatch, obeying)
    calls = done.nodes["research"].tool_calls
    page = calls[1].output or ""
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in page
    assert page.index("IGNORE ALL") < page.rindex("[End of external web content ")
    assert calls[2].is_error and "web.address_refused, metadata" in (calls[2].output or "")
    assert target not in web.requested and _no_network == []
    assert [entry.url for entry in done.sources if entry.url == target] == []
    # The agents can only search and read.
    assert all(set(node.agent.tools) == {"search_web", "fetch_web_page"} for node in workflow.nodes if node.agent)


# ---- the copy: depth, service connection and pre-checks ----------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_depth_chooses_a_researcher_with_its_own_tool_limits(language: str) -> None:
    workflow = library.build(TEMPLATE, language, services={"search": "conn_search"})
    agents = {node.id: node.agent for node in workflow.nodes if node.agent is not None}
    limits = {
        node_id: {name: settings.params["max_calls"] for name, settings in agent.tool_settings.items()}
        for node_id, agent in agents.items()
    }
    assert limits == {
        "research": {"search_web": 3, "fetch_web_page": 4},
        "research_thorough": {"search_web": 8, "fetch_web_page": 12},
    }
    assert all(agent.tool_settings["search_web"].connection_id == "conn_search" for agent in agents.values())
    assert all(agent.tool_settings["fetch_web_page"].connection_id is None for agent in agents.values())
    # Same prompt, task and result fields; only the name and the limits differ.
    first, second = agents["research"], agents["research_thorough"]
    assert first.system_prompt == second.system_prompt and first.task_template == second.task_template
    assert first.output == second.output and first.name != second.name
    sources = {field.name: field.source for field in first.output.fields}
    assert sources == {
        "answer": "model",
        "findings": "ledger_cited",
        "contradictions": "ledger_cited",
        "gaps": "model",
        "retrieved": "ledger_range",
        "sources": "ledger_list",
    }
    # Without a chosen service the copy binds no connection (the pre-check names it, see below).
    plain = library.build(TEMPLATE, language)
    assert all(
        node.agent.tool_settings["search_web"].connection_id is None for node in plain.nodes if node.agent is not None
    )
    assert library.services(TEMPLATE) == ["search"] and library.detail(TEMPLATE, language).services == ["search"]
    assert library.services("travel-plan") == []


def test_a_copy_without_a_search_service_or_offline_does_not_start(make_workspace: Any) -> None:
    workspace = make_workspace()
    workflow, _made = instantiate(workspace, TEMPLATE, "de", services={})
    check = preflight(workspace, workflow)
    # Understandable before the start: the agents' search tool has no connection.
    for node_id in RESEARCHERS:
        assert "check.connection_missing" in [issue.code for issue in check.agents[node_id]], check.agents
    connected, _made = instantiate(workspace, TEMPLATE, "de")
    assert not any(preflight(workspace, connected).agents.values())
    workspace.update_settings(SettingsIn(strict_offline=True))
    assert "check.offline_tool" in {item.code for item in preflight(workspace, connected).problems}


def test_a_local_model_without_tool_calls_is_refused_before_the_start(
    make_workspace: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = make_workspace()
    plain = InstalledModel(name="plain-model:latest", size=1, digest="0" * 64, kind="chat", capabilities=["completion"])
    service = workspace.local_models
    monkeypatch.setattr(service, "ollama_url", lambda: "http://127.0.0.1:11434")
    shown = SimpleNamespace(
        capabilities=["completion"], context_length=8192, embedding_length=None, capability_overrides=lambda: {}
    )
    client = SimpleNamespace(is_running=lambda: True, running=lambda: [], show=lambda _name: shown)
    monkeypatch.setattr(service, "client", lambda: client)
    monkeypatch.setattr(service, "installed", lambda client=None: [plain])
    models = library.model_choice(agents={node_id: "ollama:plain-model" for node_id in RESEARCHERS})
    made = library.instantiate(TEMPLATE, "en", _Host(workspace), models=models, services={})
    workflow = workspace.save_workflow(made.workflow)
    found = {(item.code, item.node_id) for item in preflight(workspace, workflow).problems}
    assert {("check.local_model_no_tools", node_id) for node_id in RESEARCHERS} <= found


class _Host:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def save_workflow(self, workflow: Any) -> tuple[str, int | None]:
        saved = self.workspace.save_workflow(workflow)
        return saved.id, self.workspace.current_version(saved)

    def add_knowledge(self, data: bytes, **kwargs: Any) -> str:
        raise AssertionError("the example has no knowledge files")
