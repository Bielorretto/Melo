"""Tests du projet push_swap (Common Core).

push_swap est un programme, pas une lib : Melo copie le rendu dans un dossier temporaire,
le compile avec le Makefile de l'élève, puis lance push_swap sur des piles mélangées.
Les instructions sont vérifiées par le checker de Melo (simulation des piles en Python),
donc pas besoin de checker_linux ni de fedora_checker.

Sections : make, erreurs, petits, 100, 500, norme, readme.
"""

import itertools
import os
import random
import shutil
import subprocess
import tempfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from core.project import (_is_melo, _ko, _make_env, _make_failure, _ok, _sh, _skip,
                          check_norm, check_readme, load_project)
from core.report import counts, print_results
from core.runner import TestResult

console = Console()

INT_MIN, INT_MAX = -2**31, 2**31 - 1
OPS = {"sa", "sb", "ss", "pa", "pb", "ra", "rb", "rr", "rra", "rrb", "rrr"}

# Barème de correction 42 (points selon le nombre d'instructions).
SCALES = {100: [700, 900, 1100, 1300, 1500], 500: [5500, 7000, 8500, 10000, 11500]}


# --------------------------------------------------------------------------- checker


def check_ops(numbers: List[int], output: str) -> Tuple[str, int]:
    """Rejoue les instructions : ("OK" | "KO" | "Error", nombre d'instructions)."""
    a, b = deque(numbers), deque()
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for op in lines:
        if op not in OPS:
            return "Error", len(lines)
        if op in ("sa", "ss") and len(a) > 1:
            a[0], a[1] = a[1], a[0]
        if op in ("sb", "ss") and len(b) > 1:
            b[0], b[1] = b[1], b[0]
        if op == "pa" and b:
            a.appendleft(b.popleft())
        if op == "pb" and a:
            b.appendleft(a.popleft())
        if op in ("ra", "rr") and a:
            a.rotate(-1)
        if op in ("rb", "rr") and b:
            b.rotate(-1)
        if op in ("rra", "rrr") and a:
            a.rotate(1)
        if op in ("rrb", "rrr") and b:
            b.rotate(1)
    ok = not b and all(a[i] < a[i + 1] for i in range(len(a) - 1))
    return ("OK" if ok else "KO"), len(lines)


# --------------------------------------------------------------------------- exécution


class Build:
    def __init__(self, work: Path, binary: Optional[Path], results: List[TestResult]):
        self.work, self.binary, self.results = work, binary, results


def _run(binary: Path, args: List[str], timeout: int = 10) -> Tuple[Optional[int], str, str]:
    try:
        p = subprocess.run([str(binary), *args], capture_output=True, text=True,
                           timeout=timeout, errors="replace", cwd=binary.parent)
    except subprocess.TimeoutExpired:
        return None, "", f"timeout après {timeout}s"
    return p.returncode, p.stdout, p.stderr


def _crash(rc: Optional[int]) -> Optional[str]:
    if rc is None:
        return "boucle infinie (timeout)"
    if rc < 0:
        names = {11: "segmentation fault", 6: "abort", 8: "floating point exception", 7: "bus error"}
        return names.get(-rc, f"tué par le signal {-rc}")
    return None


def build(project: dict, student_dir: Path, work: Path) -> Build:
    """Copie le rendu et vérifie le Makefile ; garde le binaire pour les autres sections."""
    name = project["program"]
    results: List[TestResult] = []
    if not (student_dir / "Makefile").is_file():
        return Build(work, None, [_ko("Makefile présent", "pas de Makefile à la racine", "Makefile")])

    def ignore(src: str, names: List[str]) -> set:
        return {n for n in names if n in (".git", name) or n.endswith(".o") or _is_melo(Path(src) / n)}

    shutil.copytree(student_dir, work, symlinks=True, ignore=ignore)
    env = _make_env()

    def make(*args: str) -> Tuple[Optional[int], str]:
        return _sh(["make", *args], work, timeout=180, env=env)

    binary = work / name
    rc, out = make()
    if rc != 0 or not binary.is_file():
        got = _make_failure(rc, out) if rc != 0 else f"{name} absent après make"
        results.append(_ko(f"make crée {name}", got, f"{name} à la racine", inp="make"))
        return Build(work, None, results)
    results.append(_ok(f"make crée {name}"))

    flags = ["-Wall", "-Wextra", "-Werror"]
    missing = [f for f in flags if f not in out]
    results.append(_ok("compilé avec -Wall -Wextra -Werror") if not missing else
                   _ko("compilé avec -Wall -Wextra -Werror", "manque : " + " ".join(missing),
                       " ".join(flags), inp="make"))

    rc, out = make()
    relink = [l for l in out.splitlines() if l.startswith(("cc ", "gcc ", "clang "))]
    results.append(_ok("pas de relink (2e make ne recompile rien)") if rc == 0 and not relink else
                   _ko("pas de relink (2e make ne recompile rien)", "\n".join(relink[:3]) or out.strip(),
                       "rien n'est recompilé", inp="make && make"))

    rc, _ = make("clean")
    left = [p.name for p in work.rglob("*.o")]
    results.append(_ok("make clean supprime les .o") if rc == 0 and not left else
                   _ko("make clean supprime les .o", ", ".join(left[:5]) or f"code {rc}", "aucun .o", inp="make clean"))

    rc, _ = make("fclean")
    results.append(_ok(f"make fclean supprime {name}") if rc == 0 and not binary.exists() else
                   _ko(f"make fclean supprime {name}", f"{name} toujours là" if rc == 0 else f"code {rc}",
                       f"{name} supprimé", inp="make fclean"))

    rc, out = make("re")
    results.append(_ok(f"make re reconstruit {name}") if rc == 0 and binary.is_file() else
                   _ko(f"make re reconstruit {name}", _make_failure(rc, out), f"{name} créé", inp="make re"))
    if not binary.is_file():
        make()
    return Build(work, binary if binary.is_file() else None, results)


def _no_binary(build_: Build, what: str) -> List[TestResult]:
    return [_skip(what, "push_swap n'a pas pu être compilé (voir la section make)")]


def check_errors(b: Build) -> List[TestResult]:
    if not b.binary:
        return _no_binary(b, "gestion des erreurs")
    cases = [
        ("caractère non numérique", ["1", "2", "a"]),
        ("doublon", ["1", "3", "2", "3"]),
        ("plus grand que INT_MAX", ["1", "2147483648"]),
        ("plus petit que INT_MIN", ["-2147483649", "1"]),
        ("signe seul", ["1", "-", "2"]),
        ("nombre avec lettres", ["12a", "4"]),
    ]
    results = []
    for name, args in cases:
        rc, out, err = _run(b.binary, args)
        crash = _crash(rc)
        if crash:
            results.append(_ko(f"{name} → Error", crash, "Error\\n sur la sortie d'erreur", inp=" ".join(args)))
        elif err != "Error\n" or out:
            got = f"stdout={out[:40]!r} stderr={err[:40]!r}"
            results.append(_ko(f"{name} → Error", got, "stdout vide, stderr='Error\\n'", inp=" ".join(args)))
        else:
            results.append(_ok(f"{name} → Error"))

    silent = [
        ("sans argument : rien n'est affiché", []),
        ("un seul nombre : rien n'est affiché", ["42"]),
        ("déjà trié : aucune instruction", ["1", "2", "3", "4", "5"]),
        ("INT_MIN et INT_MAX acceptés et triés", ["2147483647", "-2147483648", "0"]),
    ]
    for name, args in silent:
        rc, out, err = _run(b.binary, args)
        crash = _crash(rc)
        if crash:
            results.append(_ko(name, crash, "pas de crash", inp=" ".join(args) or "(aucun argument)"))
            continue
        if args and int(args[0]) > int(args[-1]):  # cas à trier
            status, _ = check_ops([int(x) for x in args], out)
            results.append(_ok(name) if status == "OK" and not err else
                           _ko(name, f"checker : {status}" + (f", stderr={err.strip()!r}" if err else ""),
                               "OK", inp=" ".join(args)))
        else:
            results.append(_ok(name) if not out and not err else
                           _ko(name, f"stdout={out[:40]!r} stderr={err[:40]!r}", "rien",
                               inp=" ".join(args) or "(aucun argument)"))
    return results


def check_small(b: Build, limits: Dict[int, int]) -> List[TestResult]:
    if not b.binary:
        return _no_binary(b, "petites piles")
    rng = random.Random(42)
    groups = [(2, [[2, 1]]),
              (3, [list(p) for p in itertools.permutations([1, 2, 3])]),
              (5, [rng.sample(range(-50, 50), 5) for _ in range(40)])]
    results = []
    for size, piles in groups:
        limit = limits.get(size)
        worst, bad = 0, None
        for pile in piles:
            rc, out, _ = _run(b.binary, [str(x) for x in pile])
            crash = _crash(rc)
            status, n = ("KO", 0) if crash else check_ops(pile, out)
            worst = max(worst, n)
            if crash or status != "OK":
                bad = bad or (pile, crash or f"checker : {status}")
        label = f"{size} nombres ({len(piles)} piles)"
        if bad:
            results.append(_ko(f"{label} triés", bad[1], "OK", inp=" ".join(map(str, bad[0]))))
        elif limit is not None and worst > limit:
            results.append(_ko(f"{label} en ≤ {limit} instructions", f"jusqu'à {worst} instructions",
                               f"≤ {limit}"))
        else:
            results.append(_ok(f"{label} triés" + (f" en ≤ {limit} instructions (max {worst})" if limit else "")))
    return results


# --------------------------------------------------------------------------- séries 100 / 500


def _one_run(binary: Path, size: int, seed: int) -> Tuple[List[int], str, int]:
    pile = random.Random(seed).sample(range(1, size + 1), size)
    rc, out, _ = _run(binary, [str(x) for x in pile], timeout=20)
    crash = _crash(rc)
    if crash:
        return pile, crash, 0
    status, n = check_ops(pile, out)
    return pile, status, n


def _grade(size: int, worst: int) -> int:
    scale = SCALES.get(size)
    if not scale:
        return 0
    return next((5 - i for i, lim in enumerate(scale) if worst <= lim), 0)


def benchmark(b: Build, size: int, runs: int, limit: int) -> bool:
    title = f"push_swap/{size}"
    if not b.binary:
        print_results(title, _no_binary(b, f"{runs} piles de {size} nombres"))
        return False

    seeds = [random.randrange(1 << 30) for _ in range(runs)]
    stats: List[Tuple[List[int], str, int]] = []
    console.print()
    with Progress(TextColumn(f"[cyan]🚵 {size} nombres[/]"), BarColumn(bar_width=40, complete_style="green"),
                  MofNCompleteColumn(), TextColumn("[dim]{task.fields[last]}[/]"),
                  console=console, transient=True) as progress:
        task = progress.add_task("", total=runs, last="")
        with ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 4)) as pool:
            for res in pool.map(lambda s: _one_run(b.binary, size, s), seeds):
                stats.append(res)
                color = "green" if res[1] == "OK" else "red"
                progress.update(task, advance=1, last=f"dernier : {res[2]} ops [{color}]{res[1]}[/]")

    errors = [s for s in stats if s[1] != "OK"]
    ops = [s[2] for s in stats if s[1] == "OK"] or [0]
    avg, worst, best = sum(ops) // len(ops), max(ops), min(ops)
    over = sum(1 for n in ops if n > limit)
    ok = not errors and worst <= limit

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column(justify="right")
    grid.add_column()
    grid.add_row("Runs", str(runs), "")
    grid.add_row("Erreurs", f"[{'green' if not errors else 'red'}]{len(errors)}[/]",
                 "" if not errors else f"[red]{errors[0][1]}[/]")
    grid.add_row("Moyenne", f"{avg}", "ops")
    grid.add_row("Max", f"[{'green' if worst <= limit else 'red'}]{worst}[/]", "ops")
    grid.add_row("Min", f"{best}", "ops")

    # Barre : max par rapport au seuil de la note max.
    width = 36
    filled = min(width, round(worst / max(limit, 1) * width * 0.8))
    mark = round(width * 0.8)
    bar = Text()
    bar.append("█" * filled, style="green" if worst <= limit else "red")
    bar.append("░" * (width - filled), style="grey35")
    bar = Text.assemble(bar[:mark], ("│", "bold yellow"), bar[mark:])
    grid.add_row("", bar, f"[yellow]{limit}[/]")

    points = _grade(size, worst)
    if errors:
        verdict = f"[red]❌ {len(errors)} pile(s) mal triée(s)[/]"
    elif ok:
        verdict = f"[green]✅ note max : toutes les piles en ≤ {limit} ops[/]"
    else:
        verdict = f"[red]⚠ {over} run(s) au-dessus de {limit} ops[/]"
    body = Table.grid()
    body.add_row(grid)
    body.add_row("")
    body.add_row(Text.from_markup(verdict))
    if SCALES.get(size):
        stars = "★" * points + "☆" * (5 - points)
        body.add_row(Text.from_markup(f"[dim]barème :[/] [yellow]{stars}[/] [dim]{points}/5 points[/]"))
    if errors:
        ko_file = Path(tempfile.gettempdir()) / f"melo_push_swap_ko_{size}.txt"
        ko_file.write_text(" ".join(map(str, errors[0][0])) + "\n")
        body.add_row(Text.from_markup(f"[dim]pile en échec : {ko_file}[/]"))

    console.print(Panel(body, title=f"🚵 RÉSULTATS — {size} nombres 🚵", border_style="green" if ok else "red",
                        expand=False, padding=(1, 3)))
    return ok


# --------------------------------------------------------------------------- orchestration


def run_push_swap(project_dir: Path, student_dir: Path, only: Optional[str] = None) -> bool:
    project = load_project(project_dir)
    sections = [str(s) for s in project["sections"]]
    key = only.strip("/").lower() if only else None
    if key and key not in sections:
        console.print(f"[red]'{only}' introuvable dans push_swap.[/] Sections : {', '.join(sections)}")
        return False
    wanted = [key] if key else sections

    if not student_dir.is_dir() or not list(student_dir.glob("*.c")):
        console.print(f"[red]Aucun .c dans {student_dir}.[/]")
        console.print("  clone Melo dans le dossier de ton push_swap : Melo teste son dossier parent.")
        return False

    bench = project.get("benchmarks", {})
    all_ok = True
    with tempfile.TemporaryDirectory(prefix="melo_push_swap_") as tmp:
        needs_build = any(s not in ("norme", "readme") for s in wanted)
        b = build(project, student_dir, Path(tmp) / "rendu") if needs_build else None
        simple: Dict[str, Callable[[], List[TestResult]]] = {
            "make": lambda: b.results,
            "erreurs": lambda: check_errors(b),
            "petits": lambda: check_small(b, {int(k): v for k, v in project.get("small_limits", {}).items()}),
            "norme": lambda: check_norm(project, student_dir),
            "readme": lambda: check_readme(project, student_dir),
        }
        totals = [0, 0]
        for s in wanted:
            if s in bench:
                cfg = bench[s]
                ok = benchmark(b, cfg["size"], cfg["runs"], cfg["limit"])
            else:
                results = simple[s]()
                ok = print_results(f"push_swap/{s}", results, compact=len(wanted) > 1)
                passed, total, _ = counts(results)
                totals[0] += passed
                totals[1] += total
            all_ok = all_ok and ok

    if len(wanted) > 1:
        color = "green" if all_ok else "red"
        console.print(f"\n[{color}]=== push_swap : {totals[0]}/{totals[1]} tests réussis"
                      f" + séries {' / '.join(bench)} {'✅' if all_ok else '❌'} ===[/]")
    return all_ok
