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
        elif "Error" in line:
            problems.append(f"{current or '?'} : {line.strip()}")
    return status, problems


def _is_melo(path: Path) -> bool:
    path = path.resolve()
    return path == MELO_ROOT or MELO_ROOT in path.parents


def find_sources(student_dir: Path, target: Optional[str] = None) -> List[Path]:
    """Tous les .c / .h du rendu (hors Melo et dossiers cachés), filtrés par cible."""
    files = []
    for p in sorted([*student_dir.rglob("*.c"), *student_dir.rglob("*.h")]):
        rel = p.relative_to(student_dir)
        if not p.is_file() or _is_melo(p) or any(part.startswith(".") for part in rel.parts):
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


def _fix(files: List[Path], student_dir: Path) -> bool:
    cmd = _formatter_cmd()
    if cmd is None:
        console.print("[red]c_formatter_42 n'est pas installé.[/] Installe-le avec : "
                      "[bold]pip install c-formatter-42[/]")
        return False

    backup = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
    changed = []
    for f in files:
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
            changed.append(f)

    if changed:
        console.print(f"[green]{len(changed)} fichier(s) reformaté(s)[/] "
                      f"[dim](originaux sauvegardés dans {backup})[/]")
        for f in changed:
            console.print(f"  ✏️  {f.relative_to(student_dir)}")
    else:
        console.print("[green]Rien à reformater.[/]")
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
        answer = input(f"Reformater {len(files)} fichier(s) avec c_formatter_42 ? "
                       f"(une copie est gardée) [o/N] ").strip().lower()
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
                console.print(f"       {p[len(f) + 1:].strip()}", highlight=False)

    color = "green" if not ko and proc.returncode == 0 else "red"
    console.print(f"\n[{color}]norminette : {len(ok)}/{len(status) or len(files)} fichier(s) OK[/]")
    if ko and "--fix" not in flags and "-f" not in flags:
        console.print("[dim]norme --fix reformate automatiquement la mise en forme "
                      "(tabs, espaces, accolades...).[/]")
