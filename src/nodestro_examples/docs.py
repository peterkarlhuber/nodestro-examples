"""The per-example part of the documentation chapter "beispiele", generated from the templates.

The handwritten chapter (frontend/src/docs/chapters/<language>/beispiele.md in nodestro-studio)
explains the gallery; everything between the two markers below is written by this module, so the
documentation of each example always matches its template. After changing a template run

    python -m nodestro_examples.docs [--root PATH_TO_NODESTRO_STUDIO] [--check]

``--root`` defaults to the current directory (the studio's ``make example-docs`` runs it there);
``--check`` writes nothing and exits with 1 while a chapter is out of date. A test of the studio
fails while the chapters are out of date. Text outside the markers is never changed; a chapter with
broken markers is refused instead of being rewritten.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import tempfile

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


#: Labels of format 2 (teams, knowledge, integrations, loops, limits).
_MORE: dict[str, dict[str, str]] = {
    "de": {
        "adaptive": "adaptiv (Orchestrierung)",
        "orchestrator": "Orchestrator mit Teams",
        "knowledge": "Wissensdateien",
        "integration": "optionale MCP-Anbindung",
        "loop": "Überarbeitungsschleife",
        "budget": "Budget und Grenzen",
        "contract": "Ausgabevertrag",
        "control": "Was automatisch entschieden wird und wann ein Mensch eingreift",
        "why": "Warum diese Architektur",
        "teams": "Teams, die der Orchestrator einsetzen kann",
        "team": "Team",
        "capabilities": "Fähigkeiten",
        "team_approval": "hält für eine Freigabe an",
        "parameters": "Parameter",
        "integrations": "Optionale Anbindung",
        "offline": "Ohne Anbindung",
        "setup": "Einrichtung",
        "knowledge_files": "Wissensdateien (synthetisch, werden beim Kopieren angelegt)",
        "orchestrator_kind": "Orchestrator",
    },
    "en": {
        "adaptive": "adaptive (orchestration)",
        "orchestrator": "orchestrator with teams",
        "knowledge": "knowledge files",
        "integration": "optional MCP connection",
        "loop": "revision loop",
        "budget": "budget and limits",
        "contract": "output contract",
        "control": "What is decided automatically and when a person steps in",
        "why": "Why this architecture",
        "teams": "Teams the orchestrator can deploy",
        "team": "Team",
        "capabilities": "Capabilities",
        "team_approval": "stops for an approval",
        "parameters": "Parameters",
        "integrations": "Optional connection",
        "offline": "Without a connection",
        "setup": "Setup",
        "knowledge_files": "Knowledge files (synthetic, created when copying)",
        "orchestrator_kind": "Orchestrator",
    },
    "es": {
        "adaptive": "adaptativo (orquestación)",
        "orchestrator": "orquestador con equipos",
        "knowledge": "archivos de conocimiento",
        "integration": "conexión MCP opcional",
        "loop": "bucle de revisión",
        "budget": "presupuesto y límites",
        "contract": "contrato de salida",
        "control": "Qué se decide automáticamente y cuándo interviene una persona",
        "why": "Por qué esta arquitectura",
        "teams": "Equipos que el orquestador puede emplear",
        "team": "Equipo",
        "capabilities": "Capacidades",
        "team_approval": "se detiene para una aprobación",
        "parameters": "Parámetros",
        "integrations": "Conexión opcional",
        "offline": "Sin conexión",
        "setup": "Configuración",
        "knowledge_files": "Archivos de conocimiento (sintéticos, se crean al copiar)",
        "orchestrator_kind": "Orquestador",
    },
    "fr": {
        "adaptive": "adaptatif (orchestration)",
        "orchestrator": "orchestrateur avec équipes",
        "knowledge": "fichiers de connaissances",
        "integration": "connexion MCP facultative",
        "loop": "boucle de révision",
        "budget": "budget et limites",
        "contract": "contrat de sortie",
        "control": "Ce qui est décidé automatiquement et quand une personne intervient",
        "why": "Pourquoi cette architecture",
        "teams": "Équipes que l'orchestrateur peut mobiliser",
        "team": "Équipe",
        "capabilities": "Capacités",
        "team_approval": "s'arrête pour une validation",
        "parameters": "Paramètres",
        "integrations": "Connexion facultative",
        "offline": "Sans connexion",
        "setup": "Mise en place",
        "knowledge_files": "Fichiers de connaissances (synthétiques, créés lors de la copie)",
        "orchestrator_kind": "Orchestrateur",
    },
    "pt-BR": {
        "adaptive": "adaptativo (orquestração)",
        "orchestrator": "orquestrador com equipes",
        "knowledge": "arquivos de conhecimento",
        "integration": "conexão MCP opcional",
        "loop": "ciclo de revisão",
        "budget": "orçamento e limites",
        "contract": "contrato de saída",
        "control": "O que é decidido automaticamente e quando uma pessoa intervém",
        "why": "Por que esta arquitetura",
        "teams": "Equipes que o orquestrador pode acionar",
        "team": "Equipe",
        "capabilities": "Capacidades",
        "team_approval": "para por uma liberação",
        "parameters": "Parâmetros",
        "integrations": "Conexão opcional",
        "offline": "Sem conexão",
        "setup": "Configuração",
        "knowledge_files": "Arquivos de conhecimento (sintéticos, criados ao copiar)",
        "orchestrator_kind": "Orquestrador",
    },
    "it": {
        "adaptive": "adattivo (orchestrazione)",
        "orchestrator": "orchestratore con team",
        "knowledge": "file di conoscenza",
        "integration": "collegamento MCP facoltativo",
        "loop": "ciclo di revisione",
        "budget": "budget e limiti",
        "contract": "contratto di output",
        "control": "Che cosa viene deciso automaticamente e quando interviene una persona",
        "why": "Perché questa architettura",
        "teams": "Team che l'orchestratore può impiegare",
        "team": "Team",
        "capabilities": "Capacità",
        "team_approval": "si ferma per un'approvazione",
        "parameters": "Parametri",
        "integrations": "Collegamento facoltativo",
        "offline": "Senza collegamento",
        "setup": "Configurazione",
        "knowledge_files": "File di conoscenza (sintetici, creati durante la copia)",
        "orchestrator_kind": "Orchestratore",
    },
}
for _language, _extra in _MORE.items():
    _LABELS[_language].update(_extra)


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


#: Features shown as building blocks of an example (beyond agents and tools).
_BLOCKS = (
    *("orchestrator", "decision", "approval", "loop", "form", "subworkflow", "files", "documents"),
    *("proposals", "memory", "knowledge", "integration", "contract", "budget"),
)


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
            extras = [labels["orchestrator_kind"]] if agent.kind == "orchestrator" else []
            if agent.judge:
                extras.append(labels["judge"])
            if agent.structured:
                extras.append(labels["structured"])
            if agent.tools:
                extras.append(f"{labels['tools']}: " + ", ".join(f"`{tool}`" for tool in agent.tools))
            task = agent.description + (f" ({'; '.join(extras)})" if extras else "")
            lines.append(f"| **{_cell(agent.name)}** | {_cell(task)} | {_cell(', '.join(agent.receives))} |")
        if example.team_details:
            lines += ["", f"**{labels['teams']}:**", ""]
            lines.append(f"| {labels['team']} | {labels['task']} | {labels['capabilities']} |")
            lines.append("|---|---|---|")
            for team in example.team_details:
                notes = [labels["team_approval"]] if team.approval else []
                if team.parameters:
                    notes.append(f"{labels['parameters']}: " + ", ".join(team.parameters))
                task = team.description + (f" ({'; '.join(notes)})" if notes else "")
                lines.append(f"| **{_cell(team.name)}** | {_cell(task)} | {_cell(', '.join(team.capabilities))} |")
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
            f"**{labels['control']}:** {example.guide.control}",
            "",
            f"**{labels['why']}:** {example.guide.why}",
        ]
        if example.knowledge:
            names = "; ".join(f"{item.name}: {item.description}" for item in example.knowledge)
            lines += ["", f"**{labels['knowledge_files']}:** {names}"]
        for integration in example.integrations:
            tools = ", ".join(f"`{tool}`" for tool in integration.tools)
            lines += [
                "",
                f"**{labels['integrations']}: {integration.name}** ({labels['tools']}: {tools}). "
                f"{integration.description}",
                "",
                f"**{labels['setup']}:** {integration.setup}",
                "",
                f"**{labels['offline']}:** {integration.offline}",
            ]
        lines += ["", f"**{labels['adapt']}:** {example.guide.adapt}"]
    lines += ["", END]
    return "\n".join(lines)


_PART = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def updated(chapter: str, language: str) -> str:
    """The chapter text with its generated part replaced (or appended if it has none yet).

    Raises ``ValueError`` when the markers are broken: only one of them, more than one pair, or
    the end before the start; nothing handwritten is ever overwritten by guessing.
    """
    starts, ends = chapter.count(START), chapter.count(END)
    if starts != ends or starts > 1 or (starts == 1 and chapter.index(END) < chapter.index(START)):
        raise ValueError(f"the chapter needs exactly one {START} … {END} pair (found {starts} and {ends})")
    part = render(language)
    if starts:
        return _PART.sub(lambda _match: part, chapter)
    return chapter.rstrip("\n") + "\n\n" + part + "\n"


def _write(path: Path, text: str) -> None:
    """Replace ``path`` in one step, so an interrupted run never leaves half a chapter."""
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nodestro_examples.docs", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(), help="the nodestro-studio checkout (default: .)")
    parser.add_argument("--check", action="store_true", help="only report chapters that are out of date")
    args = parser.parse_args(argv)
    stale = []
    for language in LANGUAGES:
        path = args.root / CHAPTERS / language / "beispiele.md"
        try:
            text = path.read_text(encoding="utf-8")
            new = updated(text, language)
        except (OSError, ValueError) as error:
            print(f"error: {path}: {error}", file=sys.stderr)
            return 2
        if new == text:
            continue
        stale.append(path)
        if not args.check:
            try:
                _write(path, new)
            except OSError as error:
                print(f"error: {path}: {error}", file=sys.stderr)
                return 2
            print(f"updated {path}")
    if args.check and stale:
        print("out of date: " + ", ".join(str(path) for path in stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
