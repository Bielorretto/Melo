
import re
from typing import List, Optional, Tuple

from core.cc_errors import short as short_cc_error
from core.runner import TestResult

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# --verbose : sortie complète du compilateur au lieu du résumé.
VERBOSE = False

# « ft_isalpha(97) = 1024 » / « ft_isalpha(97) = 1 » -> appel « ft_isalpha(97) ».
_CALL_RESULT_RE = re.compile(r"^(?P<call>\w+\(.*\)) = (?P<value>.*)$")
_CHAR_ARG_RE = re.compile(r"^(?P<f>\w+)\((?P<n>-?\d+)\)$")


def _print_field(label: str, value: str) -> None:
    lines = value.splitlines() or [""]
    print(f"       {label:<8} : {lines[0]}")
    for line in lines[1:]:
        print(f"       {'':<8}   {line}")


def _annotate_call(call: str) -> str:
    """ft_isalpha(97) -> ft_isalpha('a')  (97) : plus facile à lire pour un caractère."""
    m = _CHAR_ARG_RE.match(call)
    if not m:
        return call
    n = int(m.group("n"))
    if 32 <= n < 127 and chr(n) not in "'\\":
        return f"{m.group('f')}('{chr(n)}')  ({n})"
    names = {-1: "EOF", 0: "'\\0'", 9: "'\\t'", 10: "'\\n'", 127: "DEL"}
    if n in names:
        return f"{m.group('f')}({names[n]})  ({n})"
    return call


def split_call(got: str, expected: str) -> Tuple[Optional[str], str, str]:
    """Sépare l'appel des valeurs quand obtenu et attendu commencent par le même « appel = »."""
    g, e = _CALL_RESULT_RE.match(got), _CALL_RESULT_RE.match(expected)
    if g and e and g.group("call") == e.group("call"):
        return _annotate_call(g.group("call")), g.group("value"), e.group("value")
    return None, got, expected


def _print_ko(r: TestResult) -> None:
    if r.got is not None:
        print(f"  {RED}[KO]{RESET} {r.name}")
        call, got, expected = split_call(r.got, r.expected or "")
        if call:
            _print_field("appel", call)
        elif r.input:
            _print_field("appel" if re.search(r"\w+\(", r.input) else "entrée", r.input)
        _print_field("obtenu", got)
        _print_field("attendu", expected)
        if r.rule:
            _print_field("règle", r.rule)
        if r.stderr:
            _print_field("stderr", r.stderr.strip())
        print()
        return

    print(f"  {RED}[KO]{RESET} {r.name} — {r.message}")
    if r.compile_error:
        if VERBOSE:
            for line in r.compile_error.strip().splitlines():
                print(f"       {line}")
        else:
            _print_field("erreur", short_cc_error(r.compile_error))
            print(f"       {YELLOW}(sortie complète du compilateur : --verbose){RESET}")
    if r.rule:
        _print_field("règle", r.rule)
    print()


def counts(results: List[TestResult]) -> Tuple[int, int, int]:
    """(réussis, total exécutés, non exécutés)"""
    skipped = sum(1 for r in results if r.skipped)
    return sum(1 for r in results if r.passed), len(results) - skipped, skipped


def print_results(exercise_name: str, results: List[TestResult], compact: bool = False) -> bool:
    """compact=True : une section entièrement réussie tient sur une ligne."""
    passed, total, skipped = counts(results)
    all_passed = passed == total

    if compact and all_passed:
        extra = f" {YELLOW}({skipped} non exécuté(s)){RESET}" if skipped else ""
        print(f"{GREEN}[OK]{RESET} {exercise_name:<22} {passed}/{total}{extra}")
        for r in results:
            if r.skipped:
                print(f"       {YELLOW}[--]{RESET} {r.name} — {r.message}")
        return True

    print(f"\n=== {exercise_name} ===")
    for r in results:
        if r.skipped:
            print(f"  {YELLOW}[--]{RESET} {r.name} — {r.message}")
        elif r.passed:
            print(f"  {GREEN}[OK]{RESET} {r.name}")
        else:
            _print_ko(r)

    color = GREEN if all_passed else RED
    extra = f" {YELLOW}({skipped} non exécuté(s)){RESET}" if skipped else ""
    print(f"  {color}{passed}/{total} tests réussis{RESET}{extra}\n")
    return all_passed
