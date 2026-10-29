"""The example library on its own: completeness in every language and valid, consistent templates."""

from __future__ import annotations

import re
from typing import Any, get_args

from nodestro_runtime.builtin_tools import BUILTIN_TOOLS
from nodestro_runtime.graph import comment_sources, data_sources
from nodestro_runtime.schemas import LANGUAGES
import pytest

import nodestro_examples as library

IDS = library.template_ids()
#: The marker every prepared test input with sample data starts with.
SYNTHETIC = {
    "de": "SYNTHETISCHE BEISPIELDATEN",
    "en": "SYNTHETIC SAMPLE DATA",
    "es": "DATOS DE EJEMPLO SINTÉTICOS",
    "fr": "DONNÉES D'EXEMPLE SYNTHÉTIQUES",
    "pt-BR": "DADOS DE EXEMPLO SINTÉTICOS",
    "it": "DATI DI ESEMPIO SINTETICI",
}
#: The agent icons the editor can show (nodestro-studio: frontend/src/components/icons.ts).
ICONS = {
    *("bot", "search", "calculator", "check", "pen", "list", "users", "brain", "code", "globe"),
    *("book", "file", "mail", "chat", "shield", "scale", "target", "idea", "sparkles"),
}
MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"}
PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def shape(value: Any) -> Any:
    """The structure of a sample file's content: sheets, rows and columns, or the number of files."""
    if isinstance(value, dict):
        return sorted(shape(item) for item in value.values())
    if isinstance(value, list):
        return [len(value), *({len(row) for row in value if isinstance(row, list)} or {0})]
    return "text" if isinstance(value, str) else type(value).__name__


def file_fields(template_id: str) -> list[Any]:
    return [field for node in library.structure(template_id).nodes for field in node.form if field.type == "file"]


def keys_of(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        return {key for name, item in value.items() for key in keys_of(item, f"{prefix}{name}.")} | {prefix}
    return {prefix}


def test_the_library_has_24_templates_across_all_categories() -> None:
    assert len(IDS) == 24
    specs = [library.structure(template_id) for template_id in IDS]
    assert [spec.number for spec in specs] == list(range(1, 25))
    assert {spec.category for spec in specs} == set(library.CATEGORIES)
    # The two examples Nodestro shipped before are part of the library.
    assert {"financial-analysis", "blog-article"} <= set(IDS)
    assert sum(spec.featured for spec in specs) >= 6
    # Different structures: sequential chains, parallel branches, reviewers and judges.
    summaries = library.summaries("de")
    assert {item.pattern for item in summaries} == {"sequential", "parallel", "branching"}
    features = {feature for item in summaries for feature in item.features}
    assert features == set(get_args(library.Feature))
    assert all(2 <= item.agents <= 5 for item in summaries)
    # Parts used as sub-workflows are not examples of their own.
    assert all(part not in IDS for template_id in IDS for part in library.part_ids(template_id))


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_text_exists_in_every_language(language: str) -> None:
    common = library.common(language)
    assert all(value.strip() for value in common.model_dump().values())
    for template_id in IDS:
        spec = library.structure(template_id)
        german = library.raw_texts(template_id, "de")
        texts = library.raw_texts(template_id, language)
        # The content of a sample file is data in the language (sheet names, rows): same shape, own words.
        contents = {key: sample.pop("content", None) for key, sample in texts.get("samples", {}).items()}
        german_contents = {key: sample.pop("content", None) for key, sample in german.get("samples", {}).items()}
        for key, content in contents.items():
            assert shape(content) == shape(german_contents[key]), (language, template_id, key)
        assert keys_of(texts) == keys_of(german), (language, template_id)
        model = library.texts(template_id, language)
        agents = {node.id: node for node in spec.nodes if node.type == "agent"}
        assert set(model.agents) == set(agents), (language, template_id)
        steps = {node.id for node in spec.nodes if node.type in ("condition", "approval", "subworkflow")}
        assert set(model.steps) == steps, (language, template_id)
        for node in spec.nodes:
            if node.condition is not None:
                assert set(model.steps[node.id].branches) == {rule.id for rule in node.condition.rules}
                assert model.steps[node.id].default.strip()
            if node.type == "approval":
                assert model.steps[node.id].instructions.strip(), (language, template_id)
        form = {field.name for node in spec.nodes for field in node.form}
        assert set(model.form) == form, (language, template_id)
        for part_id in library.part_ids(template_id):
            part_text = library.part_texts(part_id, language)
            assert set(part_text.agents) == {node.id for node in library.part(part_id).nodes if node.type == "agent"}
            if language != "de":
                assert part_text.agents["risk"].system != library.part_texts(part_id, "de").agents["risk"].system
        for node_id, node in agents.items():
            own = model.agents[node_id]
            assert set(own.fields) == {field.name for field in node.output_fields}, (language, template_id, node_id)
            assert set(own.criteria) == set(node.criteria), (language, template_id, node_id)
            refs = sorted(re.findall(r"\{\{node:([a-z_]+)\}\}", own.task))
            source = library.texts(template_id, "de").agents[node_id].task
            assert refs == sorted(re.findall(r"\{\{node:([a-z_]+)\}\}", source))

        def strings(value: Any) -> list[str]:
            if isinstance(value, dict):
                return [item for inner in value.values() for item in strings(inner)]
            return [value]

        assert all(isinstance(item, str) and item.strip() for item in strings(texts)), (language, template_id)
        if language != "de":
            # Translated, not copied: guide and prompts differ from the German original.
            assert model.guide.problem != library.texts(template_id, "de").guide.problem, (language, template_id)
            for node_id in agents:
                assert model.agents[node_id].system != library.texts(template_id, "de").agents[node_id].system
        if template_id != "blog-article":
            assert model.input.startswith(SYNTHETIC[language]), (language, template_id)


def test_templates_only_use_what_nodestro_offers() -> None:
    tools = {tool.name for tool in BUILTIN_TOOLS}
    for template_id in IDS:
        for node in library.structure(template_id).nodes:
            if node.type != "agent":
                continue
            assert node.model in MODELS, (template_id, node.id)
            assert node.icon in ICONS, (template_id, node.id)
            assert set(node.tools) <= tools, (template_id, node.id)
            assert node.role is not None, (template_id, node.id)
        workflow = library.build(template_id, "de")
        # No server tools: they cost extra (web search) and are never needed by the examples.
        assert all(not node.agent.server_tools for node in workflow.nodes if node.agent), template_id


@pytest.mark.parametrize("language", LANGUAGES)
def test_tasks_name_every_predecessor_exactly(language: str) -> None:
    for template_id in IDS:
        workflow = library.build(template_id, language)
        labels = {node.id: node.label for node in workflow.nodes}
        names = [node.label for node in workflow.nodes if node.type == "agent"]
        assert len(set(names)) == len(names), (language, template_id)
        for node in workflow.nodes:
            if node.agent is None:
                continue
            # Decision and approval nodes pass results through: name what arrives at them.
            sources = [*data_sources(workflow, node.id), *comment_sources(workflow, node.id)]
            used = {name.lower() for name in PLACEHOLDER.findall(node.agent.task_template)}
            fields = {
                f"form.{field.name.lower()}" for item in workflow.nodes if item.start for field in item.start.fields
            }
            assert used <= {"input", "run.input", *fields, *(labels[source].lower() for source in sources)}, used
            if used & {"run.input", *fields}:
                # The run input names what the start node delivers (as the engine does).
                used |= {labels[source].lower() for source in sources if source == "start"}
            if "input" not in used:
                # Every result of a predecessor is placed on purpose, never appended as leftover.
                missing = [labels[source] for source in sources if labels[source].lower() not in used]
                assert not missing, (language, template_id, node.id, missing)
            # With several predecessors each one gets its own heading in the task.
            assert len(sources) <= 1 or "input" not in used, (language, template_id, node.id)


def test_sensitive_examples_ask_for_human_review() -> None:
    sensitive = {template_id for template_id in IDS if library.structure(template_id).sensitive}
    expected = {"financial-analysis", "hr-recruiting", "contract-review", "household-budget", "real-estate"}
    assert {*expected, "citizen-inquiry"} == sensitive
    for language in LANGUAGES:
        caution = library.common(language).caution
        for template_id in IDS:
            workflow = library.build(template_id, language)
            for node in workflow.nodes:
                if node.agent is not None:
                    prompt = node.agent.system_prompt
                    assert (caution in prompt) == (template_id in sensitive), (language, template_id)
                    assert prompt.endswith(library.common(language).answer)
                    assert library.common(language).transparency in prompt


def test_file_fields_are_optional_and_configured_like_regular_fields() -> None:
    from nodestro_runtime.file_formats import FORMATS, accepted
    from nodestro_runtime.forms import field_problems

    with_files = [template_id for template_id in IDS if file_fields(template_id)]
    # Files where the field needs them; plain text where it is enough.
    assert len(with_files) >= 15 and {"blog-article", "club-event", "business-idea"}.isdisjoint(with_files)
    for template_id in IDS:
        workflow = library.build(template_id, "de")
        start = next(node for node in workflow.nodes if node.type == "start")
        assert start.start is not None
        assert not field_problems(start.start.fields), template_id
        for field in start.start.fields:
            if field.type != "file":
                continue
            # A missing file never stops a run: every file field is optional and limits what it accepts.
            assert not field.required and field.accept, (template_id, field.name)
            assert accepted(field.accept) != set(FORMATS), (template_id, field.name)
        for sample in library.structure(template_id).samples:
            field = next(item for item in start.start.fields if item.name == sample.field)
            assert sample.format in accepted(field.accept), (template_id, sample.id)


def test_the_documents_feature_follows_the_file_fields() -> None:
    for template_id in IDS:
        features = library.summary(template_id, "de").features
        assert ("documents" in features) == bool(file_fields(template_id)), template_id
    # The template schema keeps loading files without the new settings (old defaults).
    field = library.InputSpec(name="old", type="file")
    assert (field.accept, field.multiple, field.max_files, field.delivery) == ([], True, None, "auto")
    assert library.NodeSpec(id="out", type="output", x=0, y=0, files=["pdf"]).files == ["pdf"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_sample_files_are_built_and_read_like_uploads(language: str) -> None:
    from nodestro_runtime.file_formats import detect, extract

    from nodestro_examples import samples

    built = 0
    for template_id in IDS:
        for sample_id in samples.sample_ids(template_id):
            name, _media, data = samples.render(template_id, sample_id, language)
            assert samples.render(template_id, sample_id, language)[2] == data, "the same bytes every time"
            assert len(data) < 200_000, (template_id, sample_id)
            spec = detect(name, data)
            extracted = extract(name, data, spec=spec)
            assert spec.key == next(s.format for s in library.structure(template_id).samples if s.id == sample_id)
            if spec.group != "image":
                assert extracted.chars > 80 or extracted.entries, (language, template_id, sample_id)
            built += 1
    assert built >= 20
    assert [path.name for path in samples.static_files()] == ["floor-plan.png"]


def test_agents_that_receive_files_are_told_how_to_treat_them() -> None:
    for language in LANGUAGES:
        rule = library.common(language).files
        for template_id in IDS:
            workflow = library.build(template_id, language)
            starts = {node.id for node in workflow.nodes if node.type == "start"}
            for node in workflow.nodes:
                if node.agent is None:
                    continue
                fed = any(source in starts for source in data_sources(workflow, node.id))
                expected = fed and bool(file_fields(template_id))
                assert (rule in node.agent.system_prompt) == expected, (language, template_id, node.id)


def test_result_files_proposals_and_memory_use_the_regular_settings() -> None:
    proposals: dict[str, str] = {}
    for template_id in IDS:
        workflow = library.build(template_id, "en")
        output = next(node for node in workflow.nodes if node.type == "output")
        formats = [spec.format for spec in output.output.files] if output.output else []
        assert len(formats) == len(set(formats)) <= 2, template_id
        # Reply drafts go into the ticket system, not into a file.
        assert bool(formats) == (template_id != "customer-service"), template_id
        for node in workflow.nodes:
            if node.agent and node.agent.knowledge_proposals.enabled:
                proposals[template_id] = node.agent.knowledge_proposals.content_kind
                # A person chooses the collection; nothing is preset that might not exist.
                assert node.agent.knowledge_proposals.collection == ""
            if node.agent and node.agent.memory.mode != "none":
                assert (template_id, node.id, node.agent.memory.space) == ("creator-strategy", "ideas", "creator-ideas")
            assert not (node.agent and node.agent.knowledge.file_ids), "no example needs private knowledge"
    assert proposals == {
        "quality-8d": "generated",
        "financial-analysis": "extracted",
        "research-hypotheses": "generated",
        "contract-review": "extracted",
        "nonprofit-campaign": "generated",
        "citizen-inquiry": "extracted",
    }
