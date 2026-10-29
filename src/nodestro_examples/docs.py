"""The per-example part of the documentation chapter "beispiele", generated from the templates.

The handwritten chapter (frontend/src/docs/chapters/<language>/beispiele.md) explains the
gallery; everything between the two markers below is written by this module, so the
documentation of each example always matches its template. After changing a template run

    python -m nodestro_examples.docs

in the root of nodestro-studio, where the chapters live; a test there fails while they are out of date.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

from . import detail, template_ids

START = "<!-- examples:start -->"
END = "<!-- examples:end -->"

CHAPTERS = Path("frontend/src/docs/chapters")

LANGUAGES = ("de", "en", "es", "fr", "pt-BR", "it")

_LABELS: dict[str, dict[str, str]] = {
    "de": {
        "overview": "Alle 24 Beispiele auf einen Blick",
        "overview_text": "Jedes Beispiel steht in der Galerie und hat unten einen eigenen Abschnitt.",
        "number": "Nr.",
        "example": "Beispiel",
        "field": "Bereich",
        "agents": "Agenten",
        "agent": "Agent",
        "pattern": "Muster",
        "level": "Niveau",
        "task": "Aufgabe",
        "receives": "Bekommt",
        "flow": "So arbeiten die Agenten zusammen",
        "input": "Eingabe",
        "result": "Ergebnis",
        "adapt": "Anpassen",
        "sequential": "sequenziell",
        "parallel": "parallel",
        "branching": "verzweigt",
        "blocks": "Bausteine",
        "decision": "Entscheidung",
        "approval": "Freigabe",
        "form": "Eingabeformular",
        "subworkflow": "Sub-Workflow",
        "files": "Ergebnisdateien",
        "documents": "Dateien als Eingabe",
        "proposals": "Wissensvorschläge",
        "memory": "Gedächtnis",
        "samples": "Beispieldateien",
        "tests": "Testfälle",
        "beginner": "Einsteiger",
        "advanced": "Fortgeschritten",
        "judge": "mit Qualitätsprüfung",
        "structured": "strukturierte Ausgabe",
        "tools": "Tools",
        "sensitive": "Fachlich prüfen: Die Ergebnisse sind Arbeitshilfen und müssen von einer fachkundigen Person "
        "geprüft werden.",
        "yes": "ja",
    },
    "en": {
        "overview": "All 24 examples at a glance",
        "overview_text": "Every example is in the gallery and has its own section below.",
        "number": "No.",
        "example": "Example",
        "field": "Field",
        "agents": "Agents",
        "agent": "Agent",
        "pattern": "Pattern",
        "level": "Level",
        "task": "Task",
        "receives": "Receives",
        "flow": "How the agents work together",
        "input": "Input",
        "result": "Result",
        "adapt": "Adapting it",
        "sequential": "sequential",
        "parallel": "parallel",
        "branching": "branching",
        "blocks": "Building blocks",
        "decision": "decision",
        "approval": "approval",
        "form": "input form",
        "subworkflow": "sub-workflow",
        "files": "result files",
        "documents": "files as input",
        "proposals": "knowledge proposals",
        "memory": "memory",
        "samples": "Sample files",
        "tests": "Test cases",
        "beginner": "Beginner",
        "advanced": "Advanced",
        "judge": "with quality check",
        "structured": "structured output",
        "tools": "Tools",
        "sensitive": "Needs expert check: the results are working aids and must be checked by a qualified person.",
        "yes": "yes",
    },
    "es": {
        "overview": "Los 24 ejemplos de un vistazo",
        "overview_text": "Cada ejemplo está en la galería y tiene su propia sección más abajo.",
        "number": "N.º",
        "example": "Ejemplo",
        "field": "Ámbito",
        "agents": "Agentes",
        "agent": "Agente",
        "pattern": "Patrón",
        "level": "Nivel",
        "task": "Tarea",
        "receives": "Recibe",
        "flow": "Cómo colaboran los agentes",
        "input": "Entrada",
        "result": "Resultado",
        "adapt": "Cómo adaptarlo",
        "sequential": "secuencial",
        "parallel": "paralelo",
        "branching": "con ramas",
        "blocks": "Elementos",
        "decision": "decisión",
        "approval": "aprobación",
        "form": "formulario de entrada",
        "subworkflow": "subflujo",
        "files": "archivos de resultado",
        "documents": "archivos como entrada",
        "proposals": "propuestas de conocimiento",
        "memory": "memoria",
        "samples": "Archivos de ejemplo",
        "tests": "Casos de prueba",
        "beginner": "Principiante",
        "advanced": "Avanzado",
        "judge": "con control de calidad",
        "structured": "salida estructurada",
        "tools": "Herramientas",
        "sensitive": "Requiere revisión experta: los resultados son ayudas de trabajo y una persona cualificada debe "
        "revisarlos.",
        "yes": "sí",
    },
    "fr": {
        "overview": "Les 24 exemples en un coup d'œil",
        "overview_text": "Chaque exemple se trouve dans la galerie et a sa propre section ci-dessous.",
        "number": "N°",
        "example": "Exemple",
        "field": "Domaine",
        "agents": "Agents",
        "agent": "Agent",
        "pattern": "Schéma",
        "level": "Niveau",
        "task": "Tâche",
        "receives": "Reçoit",
        "flow": "Comment les agents collaborent",
        "input": "Entrée",
        "result": "Résultat",
        "adapt": "L'adapter",
        "sequential": "séquentiel",
        "parallel": "parallèle",
        "branching": "avec branches",
        "blocks": "Éléments",
        "decision": "décision",
        "approval": "validation",
        "form": "formulaire de saisie",
        "subworkflow": "sous-workflow",
        "files": "fichiers de résultat",
        "documents": "fichiers en entrée",
        "proposals": "propositions de connaissances",
        "memory": "mémoire",
        "samples": "Fichiers d'exemple",
        "tests": "Cas de test",
        "beginner": "Débutant",
        "advanced": "Avancé",
        "judge": "avec contrôle qualité",
        "structured": "sortie structurée",
        "tools": "Outils",
        "sensitive": "Vérification experte : les résultats sont des aides au travail et doivent être vérifiés par une "
        "personne qualifiée.",
        "yes": "oui",
    },
    "pt-BR": {
        "overview": "Os 24 exemplos em resumo",
        "overview_text": "Cada exemplo está na galeria e tem sua própria seção abaixo.",
        "number": "Nº",
        "example": "Exemplo",
        "field": "Área",
        "agents": "Agentes",
        "agent": "Agente",
        "pattern": "Padrão",
        "level": "Nível",
        "task": "Tarefa",
        "receives": "Recebe",
        "flow": "Como os agentes trabalham juntos",
        "input": "Entrada",
        "result": "Resultado",
        "adapt": "Como adaptar",
        "sequential": "sequencial",
        "parallel": "paralelo",
        "branching": "com ramificações",
        "blocks": "Elementos",
        "decision": "decisão",
        "approval": "aprovação",
        "form": "formulário de entrada",
        "subworkflow": "subfluxo",
        "files": "arquivos de resultado",
        "documents": "arquivos como entrada",
        "proposals": "propostas de conhecimento",
        "memory": "memória",
        "samples": "Arquivos de exemplo",
        "tests": "Casos de teste",
        "beginner": "Iniciante",
        "advanced": "Avançado",
        "judge": "com verificação de qualidade",
        "structured": "saída estruturada",
        "tools": "Ferramentas",
        "sensitive": "Exige revisão especializada: os resultados são ferramentas de apoio e precisam ser verificados "
        "por uma pessoa qualificada.",
        "yes": "sim",
    },
    "it": {
        "overview": "I 24 esempi in sintesi",
        "overview_text": "Ogni esempio si trova nella galleria e ha una propria sezione qui sotto.",
        "number": "N.",
        "example": "Esempio",
        "field": "Ambito",
        "agents": "Agenti",
        "agent": "Agente",
        "pattern": "Schema",
        "level": "Livello",
        "task": "Compito",
        "receives": "Riceve",
        "flow": "Come collaborano gli agenti",
        "input": "Input",
        "result": "Risultato",
        "adapt": "Come adattarlo",
        "sequential": "sequenziale",
        "parallel": "parallelo",
        "branching": "con diramazioni",
        "blocks": "Elementi",
        "decision": "decisione",
        "approval": "approvazione",
        "form": "modulo di input",
        "subworkflow": "sotto-workflow",
        "files": "file di risultato",
        "documents": "file come input",
        "proposals": "proposte di conoscenza",
        "memory": "memoria",
        "samples": "File di esempio",
        "tests": "Casi di test",
        "beginner": "Principiante",
        "advanced": "Avanzato",
        "judge": "con controllo qualità",
        "structured": "output strutturato",
        "tools": "Strumenti",
        "sensitive": "Richiede verifica esperta: i risultati sono strumenti di lavoro e devono essere verificati da "
        "una persona qualificata.",
        "yes": "sì",
    },
}


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


#: Features shown as building blocks of an example (beyond agents and tools).
_BLOCKS = ("decision", "approval", "form", "subworkflow", "files", "documents", "proposals", "memory")


def render(language: str) -> str:
    """The generated Markdown for one language, including the markers."""
    labels = _LABELS[language]
    examples = [detail(template_id, language) for template_id in template_ids()]
    lines = [START, "", f"## {labels['overview']} {{#uebersicht}}", "", labels["overview_text"], ""]
    lines.append(
        f"| {labels['number']} | {labels['example']} | {labels['field']} | {labels['agents']} | {labels['pattern']} |"
    )
    lines.append("|---|---|---|---|---|")
    for example in examples:
        lines.append(
            f"| {example.number} | {_cell(example.name)} | {_cell(example.field)} | {example.agents} | "
            f"{labels[example.pattern]} |"
        )
    for example in examples:
        keywords = ", ".join([example.field.lower(), *(agent.name.lower() for agent in example.agent_details)])
        facts = [
            f"**{labels['field']}:** {example.field}",
            f"**{labels['agents']}:** {example.agents}",
            f"**{labels['pattern']}:** {labels[example.pattern]}",
            f"**{labels['level']}:** {labels[example.level]}",
        ]
        blocks = [labels[feature] for feature in _BLOCKS if feature in example.features]
        if blocks:
            facts.append(f"**{labels['blocks']}:** {', '.join(blocks)}")
        lines += [
            "",
            f"## {example.number} · {example.name} {{#{example.id}}}",
            f"<!-- keywords: {_cell(keywords)} -->",
            "",
            " · ".join(facts),
            "",
            example.guide.problem,
        ]
        if example.sensitive:
            lines += ["", f"> {labels['sensitive']}"]
        lines += ["", f"**{labels['flow']}:** {example.guide.flow}", ""]
        lines.append(f"| {labels['agent']} | {labels['task']} | {labels['receives']} |")
        lines.append("|---|---|---|")
        for agent in example.agent_details:
            extras = [labels["judge"]] if agent.judge else []
            if agent.structured:
                extras.append(labels["structured"])
            if agent.tools:
                extras.append(f"{labels['tools']}: " + ", ".join(f"`{tool}`" for tool in agent.tools))
            task = agent.description + (f" ({'; '.join(extras)})" if extras else "")
            lines.append(f"| **{_cell(agent.name)}** | {_cell(task)} | {_cell(', '.join(agent.receives))} |")
        lines += [
            "",
            f"**{labels['input']}:** {example.guide.input}",
            "",
        ]
        if example.samples:
            names = ", ".join(f"`{sample.file_name}`" for sample in example.samples)
            lines += [f"**{labels['samples']}:** {names}", ""]
        if example.tests:
            lines += [f"**{labels['tests']}:** {'; '.join(example.tests)}", ""]
        lines += [
            f"**{labels['result']}:** {example.guide.result}",
            "",
            f"**{labels['adapt']}:** {example.guide.adapt}",
        ]
    lines += ["", END]
    return "\n".join(lines)


_PART = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def updated(chapter: str, language: str) -> str:
    """The chapter text with its generated part replaced (or appended if it has none yet)."""
    part = render(language)
    if _PART.search(chapter):
        return _PART.sub(lambda _match: part, chapter)
    return chapter.rstrip("\n") + "\n\n" + part + "\n"


def main(root: Path = Path()) -> int:
    for language in LANGUAGES:
        path = root / CHAPTERS / language / "beispiele.md"
        text = path.read_text(encoding="utf-8")
        new = updated(text, language)
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
