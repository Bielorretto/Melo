
from typing import List

from core.runner import TestResult

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_results(exercise_name: str, results: List[TestResult]) -> bool:
    """Affiche les résultats un par un. Retourne True si tout est passé."""
    print(f"\n=== {exercise_name} ===")
    all_passed = True

    for r in results:
        if r.passed:
            print(f"  {GREEN}[OK]{RESET} {r.name}")
            continue

        all_passed = False
        print(f"  {RED}[KO]{RESET} {r.name} — {r.message}")

        if r.compile_error:
            print(f"       {YELLOW}compilation:{RESET}")
            for line in r.compile_error.strip().splitlines():
                print(f"       {line}")
        else:
            if r.stdout:
                print(f"       stdout obtenu : {r.stdout!r}")
            if r.stderr:
                print(f"       stderr : {r.stderr!r}")

        if r.memory and r.memory.available and not r.memory.clean:
            print(
                f"       {YELLOW}mémoire:{RESET} "
                f"{r.memory.definitely_lost} bytes perdus directement, "
                f"{r.memory.errors} erreur(s) valgrind"
            )

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    color = GREEN if passed == total else RED
    print(f"\n  {color}{passed}/{total} tests réussis{RESET}\n")
    return all_passed
