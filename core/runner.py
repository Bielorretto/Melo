
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from pathlib import Path
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


def load_manifest(exercise_dir: Path) -> dict:
    manifest_path = exercise_dir / "manifest.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _prepare_workdir(exercise_dir: Path, student_dir: Path, test: dict,
                      manifest: dict, tmp: Path) -> None:
    for src in manifest["sources"]:
        student_file = student_dir / src
        if not student_file.exists():
            raise FileNotFoundError(f"fichier manquant chez l'élève : {src}")
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


def run_test(exercise_dir: Path, student_dir: Path, test: dict,
             manifest: Optional[dict] = None, timeout: int = 5) -> TestResult:
    manifest = manifest or load_manifest(exercise_dir)

    with tempfile.TemporaryDirectory(prefix="piscine_test_") as tmp_str:
        tmp = Path(tmp_str)
        try:
            _prepare_workdir(exercise_dir, student_dir, test, manifest, tmp)
        except (FileNotFoundError, ValueError) as e:
            return TestResult(test["name"], False, str(e))

        err = _compile(tmp, manifest)
        if err:
            return TestResult(test["name"], False, "erreur de compilation", compile_error=err)

        binary = str(tmp / "test_binary")
        args = test.get("args", [])
        stdin_data = test.get("stdin", "")

        result = run_binary(binary, args, stdin_data, timeout=timeout)

        if result.timed_out:
            return TestResult(test["name"], False, "timeout : boucle infinie probable ?")

        expected_stdout = test.get("expected_stdout")
        if expected_stdout is not None and result.stdout != expected_stdout:
            return TestResult(
                test["name"], False, "stdout différent de l'attendu",
                stdout=result.stdout, stderr=result.stderr,
            )

        expected_exit = test.get("expected_exit")
        if expected_exit is not None and result.returncode != expected_exit:
            return TestResult(
                test["name"], False,
                f"exit code {result.returncode} != {expected_exit} attendu",
                stdout=result.stdout, stderr=result.stderr,
            )

        memory_report = None
        if test.get("check_memory"):
            memory_report = check_memory(binary, args, stdin_data, timeout=timeout * 2)
            if memory_report.available and not memory_report.clean:
                return TestResult(
                    test["name"], False, "leak(s) mémoire détecté(s)",
                    stdout=result.stdout, stderr=result.stderr, memory=memory_report,
                )

        return TestResult(test["name"], True, "OK", stdout=result.stdout,
                           stderr=result.stderr, memory=memory_report)

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

def run_exercise(exercise_name: str, student_dir: Path, exercises_root: Path,
                 timeout: int = 5) -> List[TestResult]:
    exercise_dir = find_exercise(exercises_root, exercise_name)
    manifest = load_manifest(exercise_dir)

    return [
        run_test(exercise_dir, student_dir, test, manifest, timeout=timeout)
        for test in manifest["tests"]
    ]
