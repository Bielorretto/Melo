"""./cli.py metrique : génère la page des statistiques et l'ouvre dans le navigateur."""

import json
import random
import tempfile
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from core.stats import StatsError, fetch_launches

TEMPLATE = Path(__file__).resolve().parent / "metrics_page.html"
PLACEHOLDER = "/*__MELO_DATA__*/null"


def demo_launches() -> List[dict]:
    """Lancements fictifs sur ~8 mois, pour voir la page sans Supabase (--demo)."""
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=240)
    rows = []
    for i in range(56):
        # Arrivées de plus en plus fréquentes avec le temps.
        first = start + timedelta(days=240 * (rng.random() ** 0.6))
        login = f"ami_{i + 1:02d}"
        t = first
        while t < now:
            rows.append({"login": login, "launched_at": t.isoformat()})
            t += timedelta(hours=rng.uniform(6, 24 * 12))
    rows.sort(key=lambda r: r["launched_at"])
    return rows


def build_page(launches: List[dict], demo: bool) -> str:
    data = {"launches": launches, "demo": demo}
    # « </ » dans un login ne doit pas pouvoir fermer la balise <script>.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise RuntimeError(f"{PLACEHOLDER} introuvable dans {TEMPLATE}")
    return html.replace(PLACEHOLDER, payload)


def run_metrique(demo: bool = False) -> int:
    if demo:
        launches = demo_launches()
    else:
        try:
            launches = fetch_launches()
        except StatsError as e:
            print(f"Impossible de récupérer les statistiques : {e}")
            print("(./cli.py metrique --demo affiche la page avec des données d'exemple)")
            return 1

    out = Path(tempfile.gettempdir()) / "melo_metrique.html"
    out.write_text(build_page(launches, demo), encoding="utf-8")
    users = len({r["login"] for r in launches})
    print(f"{users} utilisateur(s), {len(launches)} lancement(s){' (démo)' if demo else ''}")
    print(f"Page : {out}")
    if not webbrowser.open(out.as_uri()):
        print("Ouvre ce fichier dans ton navigateur.")
    return 0
