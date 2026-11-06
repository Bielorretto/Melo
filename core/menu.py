"""Menu interactif de Melo : ./cli.py melo

Piscine / Common Core  ->  Exam / Module / IA.
Dans chaque menu : un numéro, « r » pour revenir en arrière, « q » pour quitter.
"""

import shlex
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import core.report
from core.report import print_results
from core.runner import detect_module, list_modules, run_exercise

console = Console()

ROOT = Path(__file__).resolve().parent.parent
EXERCISES_ROOT = ROOT / "exercises"
EXERCISES_EXAM_ROOT = ROOT / "exercises_exam"
EXAMS_ROOT = ROOT / "exams"
RENDU_ROOT = ROOT / "rendu"
PROJECTS_ROOT = ROOT / "projects"
# Melo est cloné dans le dossier du module : le rendu est dans le dossier parent.
STUDENT_DIR = ROOT.parent

PISCINE = "piscine"
COMMON_CORE = "common_core"

BACK = ("r", "retour", "back")
QUIT = ("q", "quit", "exit")


def quit_melo() -> None:
    console.print("[yellow]À bientôt ![/]")
    sys.exit(0)


def ask(prompt: str = "") -> str:
    """Lit une ligne ; Ctrl+D / Ctrl+C quittent Melo."""
    try:
        return console.input(f"[cyan]>[/] {prompt}").strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        quit_melo()
        return ""


def choose(title: str, items: List[str], can_go_back: bool = True) -> Optional[int]:
    """Affiche une liste numérotée. Renvoie l'index choisi, ou None pour « retour »."""
    hint = "numéro, r pour revenir, q pour quitter" if can_go_back else "numéro, q pour quitter"
    while True:
        lines = "\n".join(f"[cyan]{i}[/]. {item}" for i, item in enumerate(items, start=1))
        console.print(Panel(lines, title=title, border_style="blue",
                             expand=False, padding=(0, 2)))
        choice = ask(f"choix ({hint}) : ").lower()

        if choice in QUIT:
            quit_melo()
        if can_go_back and choice in BACK:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return int(choice) - 1
        console.print("[red]Choix invalide.[/]")


# --------------------------------------------------------------------------- module


def _list_projects() -> List[str]:
    return sorted(p.parent.name for p in PROJECTS_ROOT.glob("*/project.yaml"))


def _detected_module(track: str) -> Optional[str]:
    """Le module dans lequel Melo est cloné, si on le reconnaît (comme avant)."""
    try:
        if track == PISCINE:
            return detect_module(EXERCISES_ROOT, STUDENT_DIR)
        from core.project import detect_project
        return detect_project(PROJECTS_ROOT, STUDENT_DIR)
    except Exception:
        return None


def _choose_module(track: str) -> Optional[str]:
    modules = list_modules(EXERCISES_ROOT) if track == PISCINE else _list_projects()
    if not modules:
        console.print("[red]Aucun module disponible.[/]")
        return None

    detected = _detected_module(track)
    if detected in modules:  # le module détecté en premier
        modules.remove(detected)
        modules.insert(0, detected)
    items = [f"📦 {m}" + ("  [green](détecté 📍)[/]" if m == detected else "") for m in modules]

    index = choose(f"🧪 {_track_label(track)} — modules", items)
    return None if index is None else modules[index]


def _module_help(track: str, module: str) -> None:
    one = "un seul exercice" if track == PISCINE else "une seule fonction"
    what = "exercice" if track == PISCINE else "fonction"
    rows = [
        ("🧪 test", f"teste tout {module}"),
        (f"🧪 test <{what}>", f"teste {one} (ex. test ft_strlen)"),
    ]
    if track == COMMON_CORE:
        rows += [
            ("   -h", "compile sans ton header (ex. test ft_strlen -h)"),
            ("   --strict", "vérifications plus sévères que la moulinette"),
        ]
    rows += [
        ("   -v", "sortie complète du compilateur"),
        ("🔙 retour", "revenir au menu précédent"),
        ("📄 help", "réaffiche cette aide"),
        ("🚪 quit", "quitte Melo"),
    ]
    grid = Table.grid(padding=(0, 2))
    for cmd, desc in rows:
        grid.add_row(f"[bold]{cmd}[/]", desc)
    console.print(Panel(grid, title=f"🚵 {module} — commandes 🚵",
                         border_style="green", expand=False, padding=(0, 2)))
    console.print(f"[dim]rendu testé : {STUDENT_DIR}/[/]")


def _test_piscine(module: str, target: Optional[str]) -> None:
    module_dir = EXERCISES_ROOT / module
    exo_dirs = sorted(p.parent for p in module_dir.rglob("manifest.yaml"))
    if target:
        wanted = target.strip("/").lower()
        exo_dirs = [d for d in exo_dirs
                    if d.name.lower() == wanted or d.relative_to(module_dir).as_posix().lower() == wanted]
        if not exo_dirs:
            names = ", ".join(sorted(p.parent.name for p in module_dir.rglob("manifest.yaml")))
            console.print(f"[red]'{target}' introuvable dans {module}.[/] Exercices : {names}")
            return

    for exo_dir in exo_dirs:
        exo_name = exo_dir.relative_to(EXERCISES_ROOT).as_posix()
        results = run_exercise(exo_name, STUDENT_DIR, EXERCISES_ROOT)
        print_results(exo_name, results)


def _test_project(module: str, target: Optional[str], strict: bool, no_header: bool) -> None:
    from core.project import run_project
    run_project(PROJECTS_ROOT / module, STUDENT_DIR, target, strict=strict, no_header=no_header)


def _run_test(track: str, module: str, args: List[str]) -> None:
    allowed = {"-h", "--strict", "-v"} if track == COMMON_CORE else {"-v"}
    flags = [a for a in args if a.startswith("-")]
    targets = [a for a in args if not a.startswith("-")]

    unknown = [f for f in flags if f not in allowed]
    if track == PISCINE and any(f in ("-h", "--strict") for f in unknown):
        console.print("[red]-h et --strict n'existent que pour les projets Common Core.[/]")
        return
    if unknown:
        console.print(f"[red]Option inconnue :[/] {' '.join(unknown)} — tape 'help'")
        return
    if len(targets) > 1:
        console.print("[red]Une seule fonction à la fois[/] (ou rien pour tout tester).")
        return

    target = targets[0] if targets else None
    core.report.VERBOSE = "-v" in flags
    try:
        if track == PISCINE:
            _test_piscine(module, target)
        else:
            _test_project(module, target, strict="--strict" in flags, no_header="-h" in flags)
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrompus.[/]")


def run_module(track: str) -> None:
    while True:
        module = _choose_module(track)
        if module is None:
            return

        _module_help(track, module)
        while True:
            line = ask()
            try:
                words = shlex.split(line)
            except ValueError:
                words = line.split()
            if not words:
                continue

            cmd, args = words[0].lower(), words[1:]
            if cmd in QUIT:
                quit_melo()
            if cmd in BACK:
                break
            if cmd == "help":
                _module_help(track, module)
            elif cmd == "test":
                _run_test(track, module, args)
            else:
                console.print(f"[red]Commande inconnue :[/] '{cmd}' — tape 'help'")


# --------------------------------------------------------------------------- IA


def run_chat() -> None:
    from ai.client import Assistant
    from ai.prompts import SYSTEM_CHAT

    try:
        assistant = Assistant()
    except Exception as e:
        console.print(f"[bold red]Impossible de lancer l'IA : {e}[/]")
        return
    assistant.start_chat(SYSTEM_CHAT)

    console.print("Discussion avec l'assistant piscine 42.")
    console.print("(tape 'retour' pour revenir au menu, 'q' ou 'diouf' pour arrêter, Ctrl+D marche aussi)\n")

    try:
        while True:
            try:
                user_input = console.input("[bold cyan]User: [/]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Bonne chance pour ta piscine ![/]")
                return

            if not user_input.strip():
                continue

            word = user_input.strip().lower()
            if word in BACK:
                return
            if word in ("diouf",) + QUIT:
                console.print("[yellow]Bonne chance pour ta piscine ![/]")
                sys.exit(0)

            try:
                answer = assistant.send(user_input, use_tools=True)
            except Exception as e:
                console.print(f"[bold red]Erreur : {e}[/]")
                continue

            console.print(Panel(answer, title="🚲 Melo", border_style="green", expand=False))
    finally:
        assistant.close_lldb_session()


# --------------------------------------------------------------------------- menus


def _track_label(track: str) -> str:
    return "Piscine" if track == PISCINE else "Common Core"


def run_menu() -> None:
    from exam.interactive import run_interactive_exam

    tracks = [PISCINE, COMMON_CORE]
    while True:
        t = choose("🚲 Melo", ["🏊 Piscine", "🎓 Common Core"], can_go_back=False)
        track = tracks[t]

        while True:
            action = choose(f"🚲 Melo — {_track_label(track)}",
                            ["📝 Exam", "🧪 Module", "🤖 IA"])
            if action is None:
                break
            if action == 0:
                run_interactive_exam(EXAMS_ROOT, EXERCISES_EXAM_ROOT, RENDU_ROOT, track)
            elif action == 1:
                run_module(track)
            else:
                run_chat()
