"""Commande « norme » du menu : norminette sur le code de l'élève, et --fix pour le reformater.

norme              lance norminette sur tous les .c / .h du rendu (ou sur une cible)
norme --fix        reformate d'abord avec c_formatter_42 (copie de sauvegarde), puis relance norminette

c_formatter_42 corrige la mise en forme (tabs, espaces, accolades, retours à la ligne,
alignement des déclarations...). Il ne peut pas corriger ce qui demande de réécrire le
code : fonction de plus de 25 lignes, plus de 5 fonctions par fichier, plus de 4
paramètres, déclarations au milieu du code, header 42 manquant, etc.
"""

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console

console = Console()

MELO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = MELO_ROOT / ".norme_backup"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_FILE_RE = re.compile(r"^(.+?): (OK|Error)!")
_ERR_RE = re.compile(r"^\s*Error:\s*(\S+)\s*\(line:\s*(\d+), col:\s*(\d+)\):\s*(.*)$")


def parse_norminette(output: str) -> Tuple[Dict[str, bool], List[str]]:
    """(fichier -> OK ?, liste « fichier:ligne:col CODE — message »)"""
    status: Dict[str, bool] = {}
    problems: List[str] = []
    current: Optional[str] = None
    for line in _ANSI_RE.sub("", output).splitlines():
        m = _FILE_RE.match(line)
        if m:
            current = m.group(1)
            status[current] = m.group(2) == "OK"
            continue
        m = _ERR_RE.match(line)
        if m:
            problems.append(f"{current}:{m.group(2)}:{m.group(3)} {m.group(1)} — {m.group(4).strip()}")
        elif line.strip().startswith("Error:"):
            code = line.split()[1] if len(line.split()) > 1 else ""
            problems.append(f"{current or '?'} : {_FR.get(code, line.strip())}")
    return status, problems


# Erreurs que c_formatter_42 ne sait pas corriger : il faut réécrire le code.
_MANUAL_HINTS = {
    "TOO_MANY_LINES": "fonction de plus de 25 lignes : découpe-la en fonctions plus petites",
    "TOO_MANY_FUNCS": "plus de 5 fonctions dans le fichier : déplace-en dans un autre .c",
    "TOO_MANY_ARGS": "plus de 4 paramètres : regroupe-les dans une structure",
    "TOO_MANY_VARS_FUNC": "plus de 5 variables dans la fonction : découpe-la ou utilise une structure",
    "LINE_TOO_LONG": "ligne de plus de 80 colonnes : coupe l'expression ou passe par une variable",
    "INVALID_HEADER": "header 42 manquant ou invalide : ajoute-le (vim :Stdheader, ou F1 dans VS Code)",
    "VAR_DECL_START_FUNC": "déclaration au milieu de la fonction : déclare tout au début",
    "DECL_ASSIGN_LINE": "déclaration et affectation sur la même ligne : sépare-les",
    "MULT_DECL_LINE": "plusieurs déclarations sur une ligne : une variable par ligne",
    "FORBIDDEN_CS": "structure interdite (for, do...while, switch, goto) : utilise while / if",
    "TERNARY_FBIDDEN": "ternaire interdit : remplace-le par un if / else",
    "ASSIGN_IN_CONTROL": "affectation dans un if / while : fais-la sur la ligne d'avant",
    "MULT_ASSIGN_LINE": "plusieurs affectations sur une ligne : une par ligne",
    "WRONG_SCOPE_COMMENT": "commentaire dans une fonction : mets-le au-dessus de la fonction",
    "GLOBAL_VAR_DETECTED": "variable globale interdite",
    "FORBIDDEN_TYPEDEF": "typedef interdit à cet endroit : mets-le dans un .h",
    "HEADER_PROT_ALL": "header non protégé : ajoute #ifndef / #define / #endif",
    "HEADER_PROT_NAME": "nom de la protection du header : il doit correspondre au fichier (LIBFT_H)",
    "MISSING_IDENTIFIER": "type ou nom manquant dans les paramètres",
    "EMPTY_LINE_FUNCTION": "ligne vide dans la fonction (hors après les déclarations) : supprime-la",
    "PREPROC_CONSTANT": "le préprocesseur ne doit contenir que des constantes",
}


# Erreurs de mise en forme (corrigeables par norme --fix), en français.
_FR = {
    "SPACE_REPLACE_TAB": "espace trouvé à la place d'une tabulation",
    "TAB_REPLACE_SPACE": "tabulation trouvée à la place d'un espace",
    "TOO_FEW_TAB": "il manque des tabulations pour l'indentation",
    "TOO_MANY_TAB": "trop de tabulations pour l'indentation",
    "MIXED_SPACE_TAB": "espaces et tabulations mélangés",
    "SPACE_EMPTY_LINE": "espace ou tabulation sur une ligne vide",
    "SPC_BEFORE_NL": "espace en fin de ligne",
    "CONSECUTIVE_SPC": "deux espaces à la suite",
    "CONSECUTIVE_NEWLINES": "deux lignes vides à la suite",
    "SPACE_BEFORE_FUNC": "espace avant le nom de la fonction : il faut une tabulation",
    "SPACE_AFTER_KW": "il manque un espace après le mot-clé",
    "SPC_AFTER_OPERATOR": "il manque un espace après l'opérateur",
    "SPC_BFR_OPERATOR": "il manque un espace avant l'opérateur",
    "NO_SPC_AFR_OPR": "espace en trop après l'opérateur",
    "NO_SPC_BFR_OPR": "espace en trop avant l'opérateur",
    "SPC_AFTER_PAR": "il manque un espace après la parenthèse / l'accolade / le crochet",
    "SPC_BFR_PAR": "il manque un espace avant la parenthèse / l'accolade / le crochet",
    "NO_SPC_AFR_PAR": "espace en trop après la parenthèse",
    "NO_SPC_BFR_PAR": "espace en trop avant la parenthèse",
    "SPC_AFTER_POINTER": "espace en trop après l'étoile du pointeur",
    "SPC_BFR_POINTER": "espace mal placé avant l'étoile du pointeur",
    "BRACE_NEWLINE": "l'accolade doit être seule sur sa ligne",
    "BRACE_SHOULD_EOL": "il faut un retour à la ligne après l'accolade",
    "EXP_NEWLINE": "il faut un retour à la ligne ici",
    "NEWLINE_PRECEDES_FUNC": "les fonctions doivent être séparées par une ligne vide",
    "NL_AFTER_VAR_DECL": "il faut une ligne vide après les déclarations de variables",
    "NL_AFTER_PREPROC": "il faut une ligne vide après les #include / #define",
    "MISALIGNED_VAR_DECL": "déclaration de variable mal alignée (tabulation avant le nom)",
    "MISALIGNED_FUNC_DECL": "déclaration de fonction mal alignée (tabulation avant le nom)",
    "RETURN_PARENTHESIS": "la valeur de return doit être entre parenthèses",
    "EMPTY_LINE_FILE_START": "ligne vide au début du fichier",
    "EMPTY_LINE_EOF": "ligne vide à la fin du fichier",
    "EMPTY_LINE_FUNCTION": "ligne vide dans la fonction (hors après les déclarations)",
    "NO_ARGS_VOID": "fonction sans paramètre : il faut écrire (void)",
    "PREPROC_BAD_INDENT": "mauvaise indentation du préprocesseur (# define dans un #if)",
    "PREPROC_START_LINE": "la directive # doit être en début de ligne",
    "INCLUDE_START_FILE": "les #include doivent être en haut du fichier",
    "INCLUDE_HEADER_ONLY": "on n'inclut que des fichiers .h",
    "MISSING_TYPEDEF_ID": "nom manquant dans le typedef",
    "USER_DEFINED_TYPEDEF": "un type défini par typedef doit commencer par t_",
    "STRUCT_TYPE_NAMING": "un nom de structure doit commencer par s_",
    "UNION_TYPE_NAMING": "un nom d'union doit commencer par u_",
    "ENUM_TYPE_NAMING": "un nom d'enum doit commencer par e_",
    "GLOBAL_VAR_NAMING": "une variable globale doit commencer par g_",
    "FORBIDDEN_CHAR_NAME": "nom invalide : seulement minuscules, chiffres et _",
    "MACRO_NAME_CAPITAL": "un nom de macro doit être en MAJUSCULES",
    "TOO_MANY_INSTR": "une seule instruction par ligne",
    "ARG_TYPE_UKN": "type de paramètre inconnu",
    "TOO_MANY_WS": "trop d'espaces",
    "INVALID_HEADER": "header 42 manquant ou invalide",
    "PARSING_ERROR": "norminette n'arrive pas à lire ce fichier",
    "LINE_TOO_LONG": "ligne de plus de 80 colonnes",
    "TOO_MANY_LINES": "fonction de plus de 25 lignes",
    "TOO_MANY_FUNCS": "plus de 5 fonctions dans le fichier",
    "TOO_MANY_ARGS": "plus de 4 paramètres",
    "TOO_MANY_VARS_FUNC": "plus de 5 variables dans la fonction",
    "FORBIDDEN_CS": "structure interdite (for, do...while, switch, goto)",
    "TERNARY_FBIDDEN": "ternaire interdit",
    "ASSIGN_IN_CONTROL": "affectation dans un if / while",
    "WRONG_SCOPE_COMMENT": "commentaire dans une fonction",
    "GLOBAL_VAR_DETECTED": "variable globale détectée",
    "MISSING_IDENTIFIER": "type ou nom manquant dans les paramètres",
}


def _fr(code: str, msg: str) -> str:
    return _FR.get(code) or _MANUAL_HINTS.get(code, msg).split(" : ")[0]


def _print_manual(problems: List[str], paths: Dict[str, str]) -> None:
    """Message de fin : ce qui reste après --fix doit être corrigé à la main."""
    console.print("\n[bold yellow]⚠️  Erreurs que Melo ne peut pas corriger automatiquement "
                  "(il faut réécrire le code) :[/]")
    for p in problems:
        m = re.match(r"^(.+?):(\d+):(\d+) (\S+) — (.*)$", p)
        if not m:
            console.print(f"  • {p}", highlight=False)
            continue
        f, line, code, msg = m.group(1), m.group(2), m.group(4), m.group(5)
        hint = _MANUAL_HINTS.get(code, msg)
        console.print(f"  • [bold]{paths.get(f, f)}[/] ligne [bold]{line}[/] : {hint} [dim]({code})[/]",
                      highlight=False)


def _is_melo(path: Path, student_dir: Path) -> bool:
    """Fichier interne de Melo (ce Melo, ou une autre copie de Melo dans le rendu)."""
    path = path.resolve()
    if path == MELO_ROOT or MELO_ROOT in path.parents:
        return True
    for parent in path.relative_to(student_dir.resolve()).parents:
        d = student_dir.resolve() / parent
        if parent != Path(".") and (d / "cli.py").is_file() and (d / "core").is_dir():
            return True
    return False


def find_sources(student_dir: Path, target: Optional[str] = None) -> List[Path]:
    """Tous les .c / .h du rendu (hors Melo et dossiers cachés), filtrés par cible."""
    files = []
    for p in sorted([*student_dir.rglob("*.c"), *student_dir.rglob("*.h")]):
        rel = p.relative_to(student_dir)
        if not p.is_file() or _is_melo(p, student_dir) or any(part.startswith(".") for part in rel.parts):
            continue
        files.append(p)
    if target:
        t = target.strip("/").lower()
        files = [p for p in files
                 if p.name.lower() in (t, f"{t}.c", f"{t}.h")
                 or any(part.lower() == t for part in p.relative_to(student_dir).parts[:-1])]
    return files


def _formatter_cmd() -> Optional[List[str]]:
    if shutil.which("c_formatter_42"):
        return ["c_formatter_42"]
    try:
        import c_formatter_42  # noqa: F401
        return [sys.executable, "-m", "c_formatter_42"]
    except ImportError:
        return None


def _install_formatter() -> Optional[List[str]]:
    console.print("[red]c_formatter_42 n'est pas installé[/] : c'est lui qui reformate ton code.")
    answer = input("L'installer maintenant (pip install --user c-formatter-42) ? [O/n] ").strip().lower()
    if answer not in ("", "o", "oui", "y", "yes"):
        console.print("[yellow]Installe-le avec : pip install c-formatter-42[/]")
        return None
    proc = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "c-formatter-42"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        console.print(f"[red]Installation échouée :[/]\n{proc.stderr.strip()[-800:]}")
        return None
    import importlib
    import site
    importlib.invalidate_caches()
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)
    console.print("[green]c_formatter_42 installé.[/]\n")
    return _formatter_cmd()


def _norm_errors(path: Path) -> Optional[int]:
    """Nombre d'erreurs norminette du fichier (None si norminette n'a pas répondu)."""
    try:
        proc = subprocess.run(["norminette", path.name], cwd=path.parent, capture_output=True,
                              text=True, timeout=60, errors="replace")
    except subprocess.TimeoutExpired:
        return None
    status, problems = parse_norminette(proc.stdout + proc.stderr)
    if not status:
        return None
    return len(problems) if not all(status.values()) else 0


def _fix(files: List[Path], student_dir: Path) -> bool:
    cmd = _formatter_cmd() or _install_formatter()
    if cmd is None:
        return False

    backup = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
    changed, reverted = [], []
    for f in files:
        before = _norm_errors(f)
        if before == 0:
            continue  # déjà à la norme : on ne touche pas au fichier
        original = f.read_text(errors="replace")
        try:
            # Mode stdin -> stdout : on n'écrit le fichier qu'une fois le formatage réussi.
            proc = subprocess.run(cmd, input=original, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            console.print(f"[red]{f.relative_to(student_dir)} : timeout de c_formatter_42[/]")
            continue
        if proc.returncode != 0 or not proc.stdout.strip():
            console.print(f"[red]{f.relative_to(student_dir)} : c_formatter_42 a échoué[/] "
                          f"{proc.stderr.strip()[:300]}")
            continue
        if proc.stdout != original:
            dest = backup / f.relative_to(student_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            f.write_text(proc.stdout)
            after = _norm_errors(f)
            if before is not None and (after is None or after >= before):
                # Le formatage n'a rien amélioré (ou a cassé) : on remet l'original.
                f.write_text(original)
                reverted.append(f)
            else:
                changed.append(f)

    if changed:
        console.print(f"[green]{len(changed)} fichier(s) reformaté(s)[/] "
                      f"[dim](originaux sauvegardés dans {backup})[/]")
        for f in changed:
            console.print(f"  ✏️  {f.relative_to(student_dir)}")
    elif not reverted:
        console.print("[green]Rien à reformater.[/]")
    for f in reverted:
        console.print(f"  [yellow]↩️  {f.relative_to(student_dir)} : le formatage n'améliorait rien, "
                      f"fichier laissé tel quel[/]")
    console.print()
    return True


def run_norme(student_dir: Path, args: List[str]) -> None:
    flags = [a for a in args if a.startswith("-")]
    targets = [a for a in args if not a.startswith("-")]
    unknown = [f for f in flags if f not in ("--fix", "-f")]
    if unknown:
        console.print(f"[red]Option inconnue :[/] {' '.join(unknown)} — tape 'help'")
        return
    if len(targets) > 1:
        console.print("[red]Une seule cible à la fois[/] (ou rien pour tout le rendu).")
        return
    target = targets[0] if targets else None

    if shutil.which("norminette") is None:
        console.print("[red]norminette n'est pas installée.[/] Installe-la avec : "
                      "[bold]pip install norminette[/]")
        return

    files = find_sources(student_dir, target)
    if not files:
        what = f"pour '{target}'" if target else f"dans {student_dir}"
        console.print(f"[yellow]Aucun fichier .c / .h trouvé {what}.[/]")
        return

    if "--fix" in flags or "-f" in flags:
        answer = input("Reformater les fichiers qui ne sont pas à la norme avec c_formatter_42 ? "
                       "(une copie est gardée) [o/N] ").strip().lower()
        if answer not in ("o", "oui", "y", "yes"):
            console.print("[yellow]Annulé.[/]")
            return
        if not _fix(files, student_dir):
            return

    rels = [str(f.relative_to(student_dir)) for f in files]
    try:
        proc = subprocess.run(["norminette", *rels], cwd=student_dir, capture_output=True,
                              text=True, timeout=300, errors="replace")
    except subprocess.TimeoutExpired:
        console.print("[red]norminette : timeout après 300s[/]")
        return
    status, problems = parse_norminette(proc.stdout + proc.stderr)

    ok = [f for f, good in status.items() if good]
    ko = [f for f, good in status.items() if not good]
    for f in ok:
        console.print(f"  [green][OK][/] {f}")
    for f in ko:
        console.print(f"  [red][KO][/] {f}")
        for p in problems:
            if p.startswith(f + ":") or p.startswith(f + " "):
                m = re.match(r"^(\d+):(\d+) (\S+) — (.*)$", p[len(f) + 1:].strip())
                if m:
                    line = f"ligne {m.group(1)}, col {m.group(2)} : {_fr(m.group(3), m.group(4))}"
                else:
                    line = p[len(f) + 1:].strip()
                console.print(f"       {line}", highlight=False)

    color = "green" if not ko and proc.returncode == 0 else "red"
    console.print(f"\n[{color}]norminette : {len(ok)}/{len(status) or len(files)} fichier(s) OK[/]")
    if ko and ("--fix" in flags or "-f" in flags):
        paths = {f.name: str(f.relative_to(student_dir)) for f in files}
        _print_manual(problems, paths)
    elif ko:
        console.print("[dim]norme --fix reformate automatiquement la mise en forme "
                      "(tabs, espaces, accolades...).[/]")
