
import json
import re
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

from core.sandbox import run_binary
from core.valgrind import MemoryReport, check_memory


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    stdout: str = ""
    stderr: str = ""
    memory: Optional[MemoryReport] = None
    compile_error: Optional[str] = None
    # Ce que le testeur a donné au code de l'élève, et la comparaison obtenu / attendu.
    input: Optional[str] = None
    got: Optional[str] = None
    expected: Optional[str] = None


def load_manifest(exercise_dir: Path) -> dict:
    manifest_path = exercise_dir / "manifest.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _find_student_file(student_dir: Path, src: str) -> Path:
    direct = student_dir / src
    if direct.exists():
        return direct
    matches = sorted(student_dir.rglob(src))
    if not matches:
        raise FileNotFoundError(f"fichier manquant chez l'élève : {src}")
    if len(matches) > 1:
        found = ", ".join(str(m.relative_to(student_dir)) for m in matches)
        raise FileNotFoundError(
            f"plusieurs fichiers '{src}' trouvés chez l'élève ({found}), impossible de choisir"
        )
    return matches[0]


def _prepare_workdir(exercise_dir: Path, student_dir: Path, test: dict,
                      manifest: dict, tmp: Path) -> None:
    for src in manifest["sources"]:
        student_file = _find_student_file(student_dir, src)
        shutil.copy(student_file, tmp / src)

    includes_dir = exercise_dir / "includes"
    if includes_dir.exists():
        for header in includes_dir.glob("*.h"):
            shutil.copy(header, tmp / header.name)

    main_path = tmp / "main.c"
    if manifest.get("own_main"):
        return
    if "main" in test:
        main_path.write_text(test["main"], encoding="utf-8")
    elif "program" in test:
        shutil.copy(exercise_dir / test["program"], main_path)
    elif "body" in test:
        prelude = manifest.get("prelude", "")
        generated = f"{prelude}\n\nint main(void)\n{{\n{test['body']}\n\treturn (0);\n}}\n"
        main_path.write_text(generated, encoding="utf-8")
    else:
        raise ValueError(
            f"test '{test['name']}' n'a ni 'main', ni 'program', ni 'body'"
        )

def _compile(tmp: Path, manifest: dict) -> Optional[str]:
    """Compile toutes les sources dans tmp. Retourne le message d'erreur, ou None si OK."""
    compile_cfg = manifest.get("compile", {})
    compiler = compile_cfg.get("compiler", "cc")
    flags = compile_cfg.get("flags", ["-Wall", "-Wextra", "-Werror"])
    extra = compile_cfg.get("extra", [])

    sources = [str(p) for p in tmp.glob("*.c")]
    binary = tmp / "test_binary"

    cmd = [compiler, *flags, *sources, *extra, "-o", str(binary)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp)
    if proc.returncode != 0:
        return proc.stderr
    return None


_PRINTF_CALL_RE = re.compile(r'^printf\("[^"]*",\s*(.+)\);$')
# print_sign(ft_strcmp(...)); -> ft_strcmp(...) : on garde l'appel au code de l'élève.
_WRAPPER_CALL_RE = re.compile(r'^(?!ft_)\w+\((ft_\w+\(.*\))\);$')
# Lignes affichées par les mains de test quand un test échoue.
_GOT_RE = re.compile(r"^\s*obtenu\s*:\s?(.*)$")
_EXPECTED_RE = re.compile(r"^\s*attendu\s*:\s?(.*)$")
_FIXED_EXPECTED_RE = re.compile(r'attendu : ((?:[^"\\]|\\")*?)\\n')

_SIGNAL_HINTS = {
    "SIGSEGV": "segmentation fault : accès mémoire invalide",
    "SIGBUS": "bus error : accès mémoire invalide",
    "SIGABRT": "abort : double free, free invalide ou assert",
    "SIGFPE": "erreur arithmétique : division par zéro ?",
    "SIGILL": "instruction illégale",
}


def describe_input(test: dict) -> Optional[str]:
    """L'entrée exacte donnée au code de l'élève par ce test."""
    if test.get("input"):
        return str(test["input"]).strip()
    if "args" in test or "stdin" in test:
        parts = ["./a.out", *(json.dumps(a, ensure_ascii=False) for a in test.get("args", []))]
        if "stdin" in test:
            parts.append(f"< stdin {json.dumps(test['stdin'], ensure_ascii=False)}")
        return " ".join(parts)
    if "body" in test:
        lines = [l.strip() for l in test["body"].strip().splitlines() if l.strip()]
        if len(lines) == 1:
            m = _PRINTF_CALL_RE.match(lines[0]) or _WRAPPER_CALL_RE.match(lines[0])
            return m.group(1) if m else lines[0].rstrip(";")
    return None


def _format_outputs(got: str, expected: str) -> Tuple[str, str]:
    if got == "" and expected != "":
        return "(rien affiché)", _format_outputs(expected, expected)[1]
    # Une seule ligne non vide des deux côtés : on affiche la valeur telle quelle.
    if ("\n" not in got.rstrip("\n") and "\n" not in expected.rstrip("\n")
            and got.endswith("\n") == expected.endswith("\n")
            and got.strip() and expected.strip()
            and got.strip() == got.rstrip("\n") and expected.strip() == expected.rstrip("\n")):
        return got.rstrip("\n"), expected.rstrip("\n")
    # Sortie longue sur plusieurs lignes : on montre la première ligne qui diffère.
    if len(got) > 80 or len(expected) > 80:
        got_lines = got.split("\n")
        exp_lines = expected.split("\n")
        for i in range(max(len(got_lines), len(exp_lines))):
            g = got_lines[i] if i < len(got_lines) else None
            e = exp_lines[i] if i < len(exp_lines) else None
            if g != e:
                fmt = lambda l: "(rien)" if l is None else json.dumps(l, ensure_ascii=False)
                return f"ligne {i + 1} : {fmt(g)}", f"ligne {i + 1} : {fmt(e)}"
    return json.dumps(got, ensure_ascii=False), json.dumps(expected, ensure_ascii=False)


def _parse_reported(stdout: str) -> Optional[Tuple[str, str]]:
    got = expected = None
    for line in stdout.splitlines():
        m = _GOT_RE.match(line)
        if m and got is None:
            got = m.group(1)
            continue
        m = _EXPECTED_RE.match(line)
        if m and expected is None:
            expected = m.group(1)
    if got is not None and expected is not None:
        return got, expected
    return None


def _describe_signal(returncode: int) -> str:
    try:
        name = signal.Signals(-returncode).name
    except ValueError:
        return f"crash : signal {-returncode}"
    hint = _SIGNAL_HINTS.get(name)
    return f"crash {name} ({hint})" if hint else f"crash {name}"


def _expected_summary(test: dict) -> str:
    expected_stdout = test.get("expected_stdout")
    if expected_stdout is not None:
        return _format_outputs(expected_stdout, expected_stdout)[1]
    if test.get("expected_stdout_prefix") is not None:
        return "début " + _format_outputs(test["expected_stdout_prefix"], test["expected_stdout_prefix"])[1]
    if test.get("expected_stdout_suffix") is not None:
        return "fin " + _format_outputs(test["expected_stdout_suffix"], test["expected_stdout_suffix"])[1]
    # Valeur attendue écrite en dur dans le message d'échec du main de test.
    code = test.get("main") or test.get("body") or ""
    fixed = {m.replace('\\"', '"') for m in _FIXED_EXPECTED_RE.findall(code) if "%" not in m}
    if len(fixed) == 1:
        return fixed.pop()
    return "le programme se termine normalement"


def run_test(exercise_dir: Path, student_dir: Path, test: dict,
             manifest: Optional[dict] = None, timeout: int = 5) -> TestResult:
    manifest = manifest or load_manifest(exercise_dir)
    name = test["name"]
    inp = describe_input(test)

    with tempfile.TemporaryDirectory(prefix="piscine_test_") as tmp_str:
        tmp = Path(tmp_str)
        try:
            _prepare_workdir(exercise_dir, student_dir, test, manifest, tmp)
        except (FileNotFoundError, ValueError) as e:
            return TestResult(name, False, str(e))

        err = _compile(tmp, manifest)
        if err:
            return TestResult(name, False, "erreur de compilation", compile_error=err)

        binary = str(tmp / "test_binary")
        args = test.get("args", [])
        stdin_data = test.get("stdin", "")

        result = run_binary(binary, args, stdin_data, timeout=timeout)

        def fail(message: str, got: str, expected: str, **extra) -> TestResult:
            return TestResult(name, False, message, stdout=result.stdout,
                              stderr=result.stderr, input=inp, got=got,
                              expected=expected, **extra)

        if result.timed_out:
            return fail("timeout",
                        f"aucune fin après {timeout}s (boucle infinie ou récursion sans fin ?)",
                        _expected_summary(test))

        if result.returncode is not None and result.returncode < 0:
            return fail("crash", _describe_signal(result.returncode), _expected_summary(test))

        expected_stdout = test.get("expected_stdout")
        if expected_stdout is not None and result.stdout != expected_stdout:
            got, expected = _format_outputs(result.stdout, expected_stdout)
            return fail("stdout différent de l'attendu", got, expected)

        prefix = test.get("expected_stdout_prefix")
        if prefix is not None and not result.stdout.startswith(prefix):
            got, expected = _format_outputs(result.stdout[:len(prefix)], prefix)
            return fail("début de sortie différent de l'attendu",
                        f"début {got}", f"début {expected}")

        suffix = test.get("expected_stdout_suffix")
        if suffix is not None and not result.stdout.endswith(suffix):
            got, expected = _format_outputs(result.stdout[-len(suffix):], suffix)
            return fail("fin de sortie différente de l'attendu",
                        f"fin {got}", f"fin {expected}")

        expected_exit = test.get("expected_exit")
        if expected_exit is not None and result.returncode != expected_exit:
            reported = _parse_reported(result.stdout)
            if reported:
                return fail("résultat différent de l'attendu", *reported)
            got = f"code de retour {result.returncode}"
            if result.stdout:
                got += f", sortie {json.dumps(result.stdout, ensure_ascii=False)}"
            return fail("code de retour différent de l'attendu",
                        got, f"code de retour {expected_exit}")

        memory_report = None
        if test.get("check_memory"):
            memory_report = check_memory(binary, args, stdin_data, timeout=timeout * 2)
            if memory_report.available and not memory_report.clean:
                lost = memory_report.definitely_lost + memory_report.indirectly_lost
                if lost < 0:
                    got = "valgrind n'a pas terminé (timeout)"
                elif lost:
                    got = f"fuite mémoire : {lost} octet(s) jamais libéré(s)"
                else:
                    first = re.search(r"==\d+== ((?:Invalid|Conditional jump|Use of uninitialised|Mismatched)[^\n]*)",
                                      memory_report.raw_output)
                    got = f"erreur mémoire valgrind : {first.group(1)}" if first else \
                        f"{memory_report.errors} erreur(s) mémoire valgrind"
                return fail("problème mémoire", got,
                            "aucune fuite ni erreur mémoire", memory=memory_report)

        return TestResult(name, True, "OK", stdout=result.stdout,
                          stderr=result.stderr, memory=memory_report, input=inp)


def find_exercise(exercises_root: Path, exercise_name: str) -> Path:
    for path in exercises_root.rglob(exercise_name):
        if path.is_dir() and (path / "manifest.yaml").exists():
            return path

    raise FileNotFoundError(
        f"Impossible de trouver l'exercice '{exercise_name}' dans '{exercises_root}'."
    )

def find_targets(exercises_root: Path, target: str) -> List[Path]:
    for path in exercises_root.rglob(target):
        if path.is_dir() and (path / "manifest.yaml").exists():
            return [path]

    for path in exercises_root.rglob(target):
        if path.is_dir():
            found = sorted(p.parent for p in path.rglob("manifest.yaml"))
            if found:
                return found

    return []

def _student_has_file(student_dir: Path, src: str) -> bool:
    if (student_dir / src).exists():
        return True
    return next(student_dir.rglob(src), None) is not None


def list_modules(exercises_root: Path) -> List[str]:
    modules = set()
    for manifest_path in exercises_root.rglob("manifest.yaml"):
        rel_parts = manifest_path.parent.relative_to(exercises_root).parts
        if len(rel_parts) >= 2:
            modules.add(rel_parts[0])
    return sorted(modules)


def detect_module(exercises_root: Path, student_dir: Path) -> str:
    modules = list_modules(exercises_root)
    if not modules:
        raise ValueError(f"aucun module trouvé dans {exercises_root}")

    name_matches = [m for m in modules if m.lower() == student_dir.name.lower()]
    if len(name_matches) == 1:
        return name_matches[0]

    scores: Dict[str, int] = {}
    for module in modules:
        count = 0
        for manifest_path in (exercises_root / module).rglob("manifest.yaml"):
            manifest = load_manifest(manifest_path.parent)
            sources = manifest.get("sources", [])
            if sources and all(_student_has_file(student_dir, s) for s in sources):
                count += 1
        if count > 0:
            scores[module] = count

    if len(scores) == 1:
        return next(iter(scores))
    if len(scores) > 1:
        ranked = ", ".join(
            f"{m} ({c} exo(s))" for m, c in sorted(scores.items(), key=lambda kv: -kv[1])
        )
        raise ValueError(
            f"plusieurs modules correspondent aux fichiers présents : {ranked} "
            f"— précise le module en argument"
        )
    raise ValueError(
        f"impossible de détecter le module automatiquement dans {student_dir} "
        f"— précise le module en argument (modules disponibles : {', '.join(modules)})"
    )


def run_exercise(exercise_name: str, student_dir: Path, exercises_root: Path,
                 timeout: int = 5) -> List[TestResult]:
    exercise_dir = find_exercise(exercises_root, exercise_name)
    manifest = load_manifest(exercise_dir)

    return [
        run_test(exercise_dir, student_dir, test, manifest, timeout=timeout)
        for test in manifest["tests"]
    ]
