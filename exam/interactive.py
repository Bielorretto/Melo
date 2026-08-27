
import random
import sys
from pathlib import Path
from typing import Dict

import yaml
from rich.console import Console
from rich.panel import Panel

from core.report import print_results
from core.runner import find_exercise, load_manifest, run_exercise

console = Console()


def show_help() -> None:
    text = (
        "[bold]📄 test[/]  compile et teste ton code\n"
        "[bold]📄 next[/]  exercice suivant du niveau\n"
        "[bold]📄 sujet[/]  réaffiche le sujet de l'exercice\n"
        "[bold]📄 re[/]    exercice précédent du niveau\n"
        "[bold]📄 help[/]  réaffiche cette aide\n"
        "[bold]📄 quit[/]  quitte le mode examen"
    )
    console.print(Panel(text, title="Commandes", border_style="green",
                         expand=False, padding=(0, 2)))


def _load_exams(exams_root: Path) -> Dict[str, dict]:
    exams = {}
    if not exams_root.exists():
        return exams
    for path in sorted(exams_root.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data.setdefault("title", path.stem)
        data.setdefault("icon", "🚵")
        exams[path.stem] = data
    return exams


def _choose_exam(exams: Dict[str, dict]) -> dict:
    ordered = list(exams.values())
    while True:
        lines = "\n".join(
            f"[cyan]{i}[/]. {data['icon']} {data['title']}"
            for i, data in enumerate(ordered, start=1)
        )
        console.print(Panel(lines, title="🏔️🏔️Exams disponibles🏔️🏔️", border_style="blue",
                             expand=False, padding=(0, 2)))
        choice = console.input("[cyan]>[/] choix (numéro, q pour quitter) : ").strip()

        if choice.lower() in ("q", "quit", "exit"):
            console.print("[yellow]À bientôt ![/]")
            sys.exit(0)

        if not choice.isdigit() or not (1 <= int(choice) <= len(ordered)):
            console.print("[red]Choix invalide.[/]")
            continue

        return ordered[int(choice) - 1]


def _choose_starting_level(exam: dict) -> int:
    levels = sorted(exam["levels"].keys())
    while True:
        text = f"niveaux : [green]{', '.join(str(l) for l in levels)}[/]"
        console.print(Panel(text, title=exam["title"], border_style="blue",
                             expand=False, padding=(0, 2)))
        choice = console.input("[cyan]>[/] niveau de départ : ").strip()

        if not choice.lstrip("-").isdigit() or int(choice) not in exam["levels"]:
            console.print("[red]Niveau invalide.[/]")
            continue

        return int(choice)


def _ensure_student_files(exercise_name: str, exercises_exam_root: Path,
                           rendu_root: Path) -> Path:
    """Crée rendu/<nom_court>/<source>.c si absent."""
    exo_dir = find_exercise(exercises_exam_root, exercise_name)
    manifest = load_manifest(exo_dir)

    folder_name = Path(exercise_name).name
    student_dir = rendu_root / folder_name
    student_dir.mkdir(parents=True, exist_ok=True)

    for source in manifest["sources"]:
        file_path = student_dir / source
        if not file_path.exists():
            file_path.write_text(
                f"/* {exercise_name} — écris ton code ici.\n"
                f" * Sujet : exercises_exam/{exercise_name}\n"
                f" */\n\n",
                encoding="utf-8",
            )

    return student_dir


def _show_readme(exercise_name: str, exercises_exam_root: Path) -> None:
    """Affiche le README.md de l'exercice (dans exercises_exam/) s'il existe,
    dans un panel dédié.
    """
    exo_dir = find_exercise(exercises_exam_root, exercise_name)
    readme_path = exo_dir / "README.md"

    if not readme_path.exists():
        return

    content = readme_path.read_text(encoding="utf-8").strip()
    if not content:
        return

    console.print(Panel(content, title=f"🚵📖 Sujet — {exercise_name}",
                         border_style="cyan", expand=False, padding=(1, 2)))


def _print_current(level: int, exo_name: str, student_dir: Path,
                    exercises_exam_root: Path) -> None:
    text = (
        f"niveau [green]{level}[/]  exercice [cyan]{exo_name}[/]\n"
        f"[dim]{student_dir}/[/]"
    )
    console.print(Panel(text, border_style="green", expand=False, padding=(0, 2)))
    _show_readme(exo_name, exercises_exam_root)


def run_interactive_exam(exams_root: Path, exercises_exam_root: Path,
                          rendu_root: Path) -> None:
    exams = _load_exams(exams_root)
    if not exams:
        console.print(f"[red]Aucun exam trouvé dans {exams_root} (*.yaml attendus).[/]")
        return

    exam = _choose_exam(exams)
    level = _choose_starting_level(exam)

    pool = exam["levels"][level]
    index = random.randrange(len(pool))
    exo_name = pool[index]
    student_dir = _ensure_student_files(exo_name, exercises_exam_root, rendu_root)

    show_help()
    _print_current(level, exo_name, student_dir, exercises_exam_root)

    while True:
        try:
            cmd = console.input("\n[cyan]>[/] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]À bientôt ![/]")
            return

        if cmd in ("quit", "exit", "q"):
            console.print("[yellow]À bientôt ![/]")
            return

        if cmd == "help":
            show_help()
            continue

        if cmd == "next":
            index = (index + 1) % len(pool)
            exo_name = pool[index]
            student_dir = _ensure_student_files(exo_name, exercises_exam_root, rendu_root)
            _print_current(level, exo_name, student_dir, exercises_exam_root)
            continue

        if cmd == "re":
            index = (index - 1) % len(pool)
            exo_name = pool[index]
            student_dir = _ensure_student_files(exo_name, exercises_exam_root, rendu_root)
            _print_current(level, exo_name, student_dir, exercises_exam_root)
            continue
        if cmd == "sujet":
            _show_readme(exo_name, exercises_exam_root)
            continue
        
        if cmd == "test":
            results = run_exercise(exo_name, student_dir, exercises_exam_root)
            passed = print_results(exo_name, results)

            if not passed:
                console.print(Panel("[bold red] ❌😥 Certains tests ont échoué.[/]",
                                     border_style="red", expand=False, padding=(0, 2)))
                continue

            console.print(Panel("[bold green] 🎉🎉🎉 Exercice réussi 🎉🎉🎉 ![/]",
                                 border_style="green", expand=False, padding=(0, 2)))
            next_level = level + 1

            if next_level not in exam["levels"]:
                console.print(Panel(
                    f"[bold green]Exam '{exam['title']}' terminé, bravo ![/]",
                    border_style="green", expand=False, padding=(0, 2),
                ))
                return

            level = next_level
            pool = exam["levels"][level]
            index = random.randrange(len(pool))
            exo_name = pool[index]
            student_dir = _ensure_student_files(exo_name, exercises_exam_root, rendu_root)
            console.print(f"[bold green]⬆ niveau supérieur débloqué : {level}[/]")
            _print_current(level, exo_name, student_dir, exercises_exam_root)
            continue

        console.print(f"[red]Commande inconnue :[/] '{cmd}' — tape 'help'")