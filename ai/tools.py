
from pathlib import Path
from typing import List


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
