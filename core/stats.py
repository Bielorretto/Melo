"""Statistiques d'utilisation de Melo, stockées dans une table Supabase.

- Au lancement (./cli.py melo), Melo ajoute une ligne (login, date) avec la clé
  publique : elle ne permet QUE d'ajouter des lignes, pas de les lire.
- ./cli.py metrique lit toutes les lignes avec la clé secrète, qui reste dans
  l'environnement (ou le .env) de la personne qui suit les stats.

MELO_NO_STATS=1 désactive l'envoi.
"""

import getpass
import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
TABLE = "melo_launches"
PAGE_SIZE = 1000


class StatsError(Exception):
    pass


def _config() -> dict:
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data.get("stats") or {}


def _headers(key: str) -> Dict[str, str]:
    # Les nouvelles clés Supabase (sb_publishable_..., sb_secret_...) passent
    # seulement dans « apikey » ; les anciennes (JWT) aussi en Bearer.
    headers = {"apikey": key}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _endpoint(cfg: dict) -> Optional[str]:
    url = (cfg.get("supabase_url") or "").strip().rstrip("/")
    return f"{url}/rest/v1/{TABLE}" if url else None


def current_login() -> str:
    login = os.environ.get("USER") or os.environ.get("LOGNAME")
    if not login:
        try:
            login = getpass.getuser()
        except Exception:
            login = "inconnu"
    return login.strip()[:64] or "inconnu"


def _send_launch(endpoint: str, key: str, login: str) -> None:
    body = json.dumps({"login": login}).encode()
    req = urllib.request.Request(endpoint, data=body, method="POST", headers={
        **_headers(key),
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        urllib.request.urlopen(req, timeout=3).close()
    except Exception:
        pass  # pas de réseau, Supabase injoignable... : Melo marche quand même


def record_launch() -> None:
    """Enregistre ce lancement en arrière-plan, sans jamais bloquer ni planter Melo."""
    if os.environ.get("MELO_NO_STATS"):
        return
    cfg = _config()
    endpoint = _endpoint(cfg)
    key = (cfg.get("publishable_key") or "").strip()
    if not endpoint or not key:
        return
    threading.Thread(target=_send_launch, args=(endpoint, key, current_login()),
                     daemon=True).start()


def fetch_launches() -> List[dict]:
    """Tous les lancements [{login, launched_at}], du plus ancien au plus récent."""
    cfg = _config()
    endpoint = _endpoint(cfg)
    if not endpoint:
        raise StatsError("stats.supabase_url est vide dans config.yaml")
    key_env = cfg.get("secret_key_env") or "MELO_SUPABASE_SECRET_KEY"
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = (os.environ.get(key_env) or "").strip()
    if not key:
        raise StatsError(f"clé secrète absente : définis {key_env} (dans ton .env ou en export)")

    rows: List[dict] = []
    start = 0
    while True:
        req = urllib.request.Request(
            f"{endpoint}?select=login,launched_at&order=launched_at.asc",
            headers={**_headers(key), "Range-Unit": "items",
                     "Range": f"{start}-{start + PAGE_SIZE - 1}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                page = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise StatsError(f"Supabase a répondu {e.code} : {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise StatsError(f"impossible de joindre Supabase : {e}") from e
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE
