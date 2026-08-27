#!/usr/bin/env python3

"""Point d'entrée du testeur piscine 42.

Usage :
  ./cli.py list
  ./cli.py test ft_strdup /chemin/vers/rendu/
  ./cli.py exam
  ./cli.py ai-explain ft_strdup
  ./cli.py ai-debug ft_strdup /chemin/vers/rendu/ "segfault sur une chaine vide"
"""
import argparse
import sys
from pathlib import Path

from core.report import print_results
from core.runner import run_exercise, find_targets
from rich.console import Console
from rich.panel import Panel

console = Console()

ROOT = Path(__file__).parent
EXERCISES_ROOT = ROOT / "exercises"
EXERCISES_EXAM_ROOT = ROOT / "exercises_exam"
EXAMS_ROOT = ROOT / "exams"
RENDU_ROOT = ROOT / "rendu"


def cmd_test(args):
    student_dir = Path(args.student_dir).resolve() if args.student_dir else ROOT.parent
    exercise_dirs = find_targets(EXERCISES_ROOT, args.exercise)

    if not exercise_dirs:
        print(f"'{args.exercise}' introuvable (ni exercice, ni module) dans {EXERCISES_ROOT}")
        sys.exit(1)

    all_ok = True
    for exo_dir in exercise_dirs:
        exo_name = exo_dir.relative_to(EXERCISES_ROOT).as_posix()
        results = run_exercise(exo_name, student_dir, EXERCISES_ROOT, timeout=args.timeout)
        ok = print_results(exo_name, results)
        all_ok = all_ok and ok

    sys.exit(0 if all_ok else 1)

def cmd_list(args):
    print("Exercices disponibles :")
    for manifest_path in sorted(EXERCISES_ROOT.rglob("manifest.yaml")):
        exo_dir = manifest_path.parent
        exo_name = exo_dir.relative_to(EXERCISES_ROOT).as_posix()
        print(f"  - {exo_name}")


def cmd_exam(args):
    from exam.interactive import run_interactive_exam
    run_interactive_exam(EXAMS_ROOT, EXERCISES_EXAM_ROOT, RENDU_ROOT)

def cmd_ai_explain(args):
    from ai.client import Assistant
    from ai.prompts import SYSTEM_EXPLAIN
    from ai.tools import get_exercise_context
    from core.runner import find_exercise

    try:
        exo_dir = find_exercise(EXERCISES_ROOT, args.exercise)
    except FileNotFoundError:
        exo_dir = find_exercise(EXERCISES_EXAM_ROOT, args.exercise)
    context = get_exercise_context(exo_dir)
    assistant = Assistant()
    print(assistant.ask(SYSTEM_EXPLAIN, f"Sujet de l'exercice :\n\n{context}"))

def cmd_ai_debug(args):
    from ai.client import Assistant
    from ai.prompts import SYSTEM_DEBUG

    student_dir = Path(args.student_dir).resolve() if args.student_dir else ROOT.parent
    hint = f"Dossier source de l'élève : {student_dir}\n(compile son code toi-même via gdb si besoin, ou demande-lui le chemin du binaire)"
    assistant = Assistant()
    answer = assistant.ask(
        SYSTEM_DEBUG,
        f"{hint}\n\nDescription du problème par l'élève :\n{args.message}",
        use_tools=True,
    )
    print(answer)


def cmd_chat(args):
    from ai.client import Assistant
    from ai.prompts import SYSTEM_CHAT

    assistant = Assistant()
    assistant.start_chat(SYSTEM_CHAT)

    print("Discussion avec l'assistant piscine 42.")
    print("(tape 'exit' ou 'quit' ou 'diouf' pour arrêter, Ctrl+D marche aussi)\n")

    while True:
        try:
            user_input = console.input("[bold cyan]User: [/]")
        except (EOFError, KeyboardInterrupt):
            console.print("[yellow]Bonne chance pour ta piscine ![/]")
            break

        if not user_input.strip():
            continue

        if user_input.lower() in ("diouf", "quit", "q"):
            console.print("[yellow]Bonne chance pour ta piscine ![/]")
            break

        try:
            answer = assistant.send(user_input)
        except Exception as e:
            console.print(f"[bold red]Erreur : {e}[/]")
            continue

        console.print(
            Panel(
                answer,
                title="🚲 Melo",
                border_style="green",
                expand=False
            )
        )

def main():
    parser = argparse.ArgumentParser(prog="piscine-tester")
    sub = parser.add_subparsers(dest="command", required=True)

    p_test = sub.add_parser("test", help="teste un exercice")
    p_test.add_argument("exercise")
    p_test.add_argument("student_dir", nargs="?", default=None,
                         help="dossier du rendu (défaut : dossier parent de Meloweo/)")
    p_test.add_argument("--timeout", type=int, default=5)
    p_test.set_defaults(func=cmd_test)

    p_list = sub.add_parser("list", help="liste les exercices disponibles")
    p_list.set_defaults(func=cmd_list)

    p_exam = sub.add_parser("exam", help="lance le mode examen interactif (menu, niveaux, next/re/test)")
    p_exam.set_defaults(func=cmd_exam)

    p_explain = sub.add_parser("ai-explain", help="explique le but d'un exercice")
    p_explain.add_argument("exercise")
    p_explain.set_defaults(func=cmd_ai_explain)

    p_chat = sub.add_parser("melo", help="discute librement avec l'IA dans le terminal")
    p_chat.add_argument(
        "--debug", action="store_true",
        help="autorise l'IA à utiliser l'outil gdb pendant la conversation",
    )
    p_chat.set_defaults(func=cmd_chat)

    p_debug = sub.add_parser("ai-debug", help="aide au debug (gdb) via le LLM")
    p_debug.add_argument("exercise")
    p_debug.add_argument("student_dir", nargs="?", default=None,
                          help="dossier du rendu (défaut : dossier parent de Meloweo/)")
    p_debug.add_argument("message", help="décris ton problème")
    p_debug.set_defaults(func=cmd_ai_debug)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
