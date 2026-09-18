
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

DEBUG_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "start_debug",
            "description": (
                "Démarre une session de debug lldb persistante sur le binaire "
                "compilé de l'élève ET lance déjà le programme, arrêté au début "
                "de main (aucun autre appel n'est nécessaire pour ça). À "
                "appeler une seule fois, avant goto_line, print_variable ou "
                "list_variables."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "binary_path": {"type": "string"},
                },
                "required": ["binary_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goto_line",
            "description": (
                "Amène l'exécution du programme jusqu'à une ligne précise d'un "
                "fichier source, peu importe si on est avant ou après dans le "
                "programme (relance depuis le début si nécessaire, il n'y a pas "
                "de retour en arrière possible en debug). Affiche le code source "
                "autour de cette ligne une fois arrivé."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "nom du fichier source, ex: ft_split.c",
                    },
                    "line": {"type": "integer"},
                },
                "required": ["file", "line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goto_function",
            "description": (
                "Amène l'exécution au tout début d'une fonction, par son nom "
                "exact (ex: 'ft_split'), quel que soit le fichier où elle est "
                "définie et sans avoir besoin de connaître le numéro de ligne. "
                "C'est le bon outil quand l'élève demande d'entrer/rentrer dans "
                "une fonction précise, plutôt que d'essayer de calculer un "
                "nombre de next/step. Relance depuis le début si nécessaire, "
                "comme goto_line."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {
                        "type": "string",
                        "description": "nom exact de la fonction, ex: ft_split",
                    },
                },
                "required": ["function"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_source",
            "description": (
                "Affiche le code source d'un fichier, en partie ou en entier, "
                "indépendamment de l'endroit où l'exécution est arrêtée. "
                "Utile quand l'élève demande de voir le code, tout le fichier, "
                "ou une zone précise, sans forcément déplacer l'exécution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "nom du fichier source, ex: ft_split.c",
                    },
                    "line": {
                        "type": "integer",
                        "description": "ligne de départ (défaut : 1, début du fichier)",
                    },
                    "count": {
                        "type": "integer",
                        "description": (
                            "nombre de lignes à afficher (défaut : 200, suffisant "
                            "pour un fichier entier d'exercice de piscine)"
                        ),
                    },
                },
                "required": ["file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "print_variable",
            "description": (
                "Affiche la valeur actuelle d'une variable ou d'une expression "
                "précise dans le contexte courant (là où goto_line s'est arrêté)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "nom de variable ou expression, ex: tab[i]",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_variables",
            "description": (
                "Liste toutes les variables locales et leur valeur actuelle dans "
                "le contexte courant (là où goto_line s'est arrêté)."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]