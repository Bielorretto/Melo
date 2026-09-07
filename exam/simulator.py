
import json
import random
import time
from pathlib import Path
from typing import List

import yaml

from core.report import print_results
from core.runner import run_exercise


def list_exercises_by_tag(exercises_root: Path, tag: str) -> List[str]:
    matching = []
    for exo_dir in exercises_root.iterdir():
        manifest_path = exo_dir / "manifest.yaml"
        if not exo_dir.is_dir() or not manifest_path.exists():
            continue
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if tag in manifest.get("tags", []):
            matching.append(exo_dir.name)
    return matching


def run_exam(exercises_root: Path, student_dir: Path, tag: str, nb_exos: int,
             duration_minutes: int, sessions_dir: Path) -> dict:
    candidates = list_exercises_by_tag(exercises_root, tag)
    if len(candidates) < nb_exos:
        raise ValueError(
            f"pas assez d'exercices pour le tag '{tag}' "
            f"({len(candidates)} disponibles, {nb_exos} demandés)"
        )
    chosen = random.sample(candidates, nb_exos)

    print(f"Examen '{tag}' — {nb_exos} exercice(s) — {duration_minutes} min")
    print(f"Exercices tirés : {', '.join(chosen)}\n")

    start = time.time()
    session = {"tag": tag, "exercises": {}}

    for exo_name in chosen:
        input(f"Appuie sur Entrée quand tu es prêt à commencer '{exo_name}'...")
        results = run_exercise(exo_name, student_dir, exercises_root)
        passed = print_results(exo_name, results)
        session["exercises"][exo_name] = {
            "passed": passed,
            "tests_ok": sum(1 for r in results if r.passed),
            "tests_total": len(results),
        }

        remaining = duration_minutes - (time.time() - start) / 60
        if remaining <= 0:
            print(f"⏰ Temps écoulé ! ({duration_minutes} min dépassées)")
            break
        print(f"Temps restant : {remaining:.1f} min\n")

    session["duration_minutes"] = round((time.time() - start) / 60, 1)
    nb_ok = sum(1 for e in session["exercises"].values() if e["passed"])
    print(f"\n=== Résultat de l'examen : {nb_ok}/{len(chosen)} exercices réussis ===")

    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"session_{int(start)}.json"
    session_file.write_text(json.dumps(session, indent=2, ensure_ascii=False))
    print(f"Session sauvegardée dans {session_file}")

    return session
