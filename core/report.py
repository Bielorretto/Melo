
from typing import List

from core.runner import TestResult

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def _print_field(label: str, value: str) -> None:
    lines = value.splitlines() or [""]
    print(f"       {label:<8} : {lines[0]}")
    for line in lines[1:]:
        print(f"       {'':<8}   {line}")


def print_results(exercise_name: str, results: List[TestResult]) -> bool:
    print(f"\n=== {exercise_name} ===")
    all_passed = True

    for r in results:
        if r.passed:
            print(f"  {GREEN}[OK]{RESET} {r.name}")
            continue

        all_passed = False

        if r.got is not None:
            print(f"  {RED}[KO]{RESET} {r.name}")
            if r.input:
                _print_field("entrée", r.input)
            _print_field("obtenu", r.got)
            _print_field("attendu", r.expected or "")
            if r.stderr:
                _print_field("stderr", r.stderr.strip())
            print()
            continue

        print(f"  {RED}[KO]{RESET} {r.name} — {r.message}")
        if r.compile_error:
            print(f"       {YELLOW}compilation:{RESET}")
            for line in r.compile_error.strip().splitlines():
                print(f"       {line}")
        print()

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    color = GREEN if passed == total else RED
    print(f"  {color}{passed}/{total} tests réussis{RESET}\n")
    return all_passed
