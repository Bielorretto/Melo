
import subprocess
from pathlib import Path
from typing import List


ALLOWED_GDB_PREFIXES = (
    "break", "b ", "run", "r", "backtrace", "bt", "print", "p ",
    "next", "n", "step", "s", "continue", "c", "list", "l",
    "info", "watch", "frame", "f ",
)


def _is_allowed(cmd: str) -> bool:
    cmd = cmd.strip()
    return any(cmd == p.strip() or cmd.startswith(p) for p in ALLOWED_GDB_PREFIXES)


def run_gdb_session(binary_path: str, commands: List[str], timeout: int = 10) -> str:
    if not Path(binary_path).exists():
        return f"Erreur : binaire introuvable ({binary_path})"

    safe_commands = [c for c in commands if _is_allowed(c)]
    rejected = [c for c in commands if c not in safe_commands]

    gdb_args = ["gdb", "--batch", "-q"]
    for c in safe_commands:
        gdb_args += ["-ex", c]
    gdb_args.append(binary_path)

    try:
        proc = subprocess.run(gdb_args, capture_output=True, text=True, timeout=timeout)
        output = proc.stdout + proc.stderr
    except FileNotFoundError:
        return "Erreur : gdb n'est pas installé sur cette machine."
    except subprocess.TimeoutExpired:
        output = "gdb : timeout (le binaire boucle probablement à l'infini)"

    if rejected:
        output += f"\n\n(commandes refusées, non autorisées : {rejected})"
    return output


def get_exercise_context(exercise_dir: Path) -> str:
    readme = exercise_dir / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    manifest = exercise_dir / "manifest.yaml"
    return manifest.read_text(encoding="utf-8") if manifest.exists() else ""


EXERCISES_ROOT = Path(__file__).parent.parent / "exercises"


def list_exercise_names() -> List[str]:
    if not EXERCISES_ROOT.exists():
        return []
    return sorted(
        p.parent.relative_to(EXERCISES_ROOT).as_posix()
        for p in EXERCISES_ROOT.rglob("manifest.yaml")
    )

def get_exercise_subject(exercise_name: str) -> str:
    exo_dir = EXERCISES_ROOT / exercise_name
    if not exo_dir.exists() or not (exo_dir / "manifest.yaml").exists():
        available = ", ".join(list_exercise_names()) or "(aucun)"
        return (
            f"Exercice '{exercise_name}' introuvable. "
            f"Exercices disponibles : {available}"
        )
    context = get_exercise_context(exo_dir)
    return context or f"Aucun README ni manifest lisible pour '{exercise_name}'."


EXERCISE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_exercises",
            "description": (
                "Liste les noms de tous les exercices disponibles dans la piscine. "
                "À utiliser si l'élève ne donne pas le nom exact de l'exercice."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exercise_subject",
            "description": (
                "Renvoie le sujet complet (README ou manifest) d'un exercice donné "
                "par son nom exact, pour pouvoir l'expliquer à l'élève sans qu'il "
                "ait à le copier-coller lui-même."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "nom exact de l'exercice, ex: ft_strdup",
                    },
                },
                "required": ["exercise_name"],
            },
        },
    },
]

DEBUG_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_gdb_session",
            "description": (
                "Lance gdb en mode batch sur le binaire compilé de l'élève avec une "
                "liste de commandes gdb (break, run, print, backtrace, next, step...). "
                "Utile pour localiser un segfault ou inspecter des variables."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "binary_path": {"type": "string"},
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "ex: ['break main', 'run', 'next', 'print *ptr']",
                    },
                },
                "required": ["binary_path", "commands"],
            },
        },
    }
]

TOOLS_SCHEMA = DEBUG_TOOLS_SCHEMA