"""Résumé lisible des erreurs de gcc/cc/ld : une ligne par erreur, en français.

    ft_strlen.c:16:9: error: conflicting types for 'ft_strlen'; have 'size_t(const char *)' ...
    libft.h:30:9: note: previous declaration of 'ft_strlen' with type 'int(const char *)'
devient
    ft_strlen.c:16  ft_strlen : type différent de sa déclaration dans libft.h:30
                    (ici size_t(const char *), là-bas int(const char *))
"""

import re
from typing import List, Optional, Tuple

_DIAG_RE = re.compile(r"^(?P<file>[^:\s][^:]*):(?P<line>\d+)(?::\d+)?:\s*"
                      r"(?P<kind>fatal error|error|warning|note):\s*(?P<msg>.*)$")
_LD_RE = re.compile(r"undefined reference to [`'‘](?P<name>[^'’]+)['’]")
_WERROR_RE = re.compile(r"\s*\[-W[^\]]*\]\s*$")

# (motif sur le message gcc, traduction). Les groupes nommés sont réutilisés.
_TRANSLATIONS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"conflicting types for '(?P<a>[^']+)'(?:; have '(?P<b>[^']+)')?"),
     "{a} : type différent de sa déclaration"),
    (re.compile(r"unused parameter '(?P<a>[^']+)'"), "paramètre {a} jamais utilisé"),
    (re.compile(r"unused variable '(?P<a>[^']+)'"), "variable {a} jamais utilisée"),
    (re.compile(r"variable '(?P<a>[^']+)' set but not used"), "variable {a} affectée mais jamais lue"),
    (re.compile(r"'(?P<a>[^']+)' defined but not used"), "{a} définie mais jamais utilisée"),
    (re.compile(r"implicit declaration of function '(?P<a>[^']+)'"),
     "{a} appelée sans être déclarée (include ou prototype manquant)"),
    (re.compile(r"unknown type name '(?P<a>[^']+)'"), "type {a} inconnu (include manquant ?)"),
    (re.compile(r"'(?P<a>[^']+)' undeclared"), "{a} non déclaré"),
    (re.compile(r"(?P<a>\S+): No such file or directory"), "fichier {a} introuvable"),
    (re.compile(r"comparison of integer expressions of different signedness: '(?P<a>[^']+)'"
                r"(?: \{aka [^}]*\})? and '(?P<b>[^']+)'"),
     "comparaison entre un signé et un non signé ({a} et {b})"),
    (re.compile(r"control reaches end of non-void function"), "fin de fonction atteinte sans return"),
    (re.compile(r"expected '(?P<a>[^']+)' before '(?P<b>[^']+)' token"), "il manque « {a} » avant « {b} »"),
    (re.compile(r"expected '(?P<a>[^']+)' before (?P<b>.*)"), "il manque « {a} » avant {b}"),
    (re.compile(r"expected (?P<a>.*)"), "syntaxe : attendu {a}"),
    (re.compile(r"too few arguments to function '(?P<a>[^']+)'"), "pas assez d'arguments pour {a}"),
    (re.compile(r"too many arguments to function '(?P<a>[^']+)'"), "trop d'arguments pour {a}"),
    (re.compile(r"redefinition of '(?P<a>[^']+)'"), "{a} défini deux fois"),
    (re.compile(r"'return' with a value, in function returning void"),
     "return avec une valeur dans une fonction void"),
    (re.compile(r"'return' with no value, in function returning non-void"),
     "return sans valeur dans une fonction qui doit renvoyer quelque chose"),
    (re.compile(r"(?:assignment|initialization) discards '(?P<a>[^']+)' qualifier"),
     "le qualificatif {a} est perdu (cast manquant ?)"),
    (re.compile(r"passing argument (?P<a>\d+) of '(?P<b>[^']+)'.*"),
     "argument {a} de {b} : mauvais type"),
    (re.compile(r"'(?P<a>[^']+)' is used uninitialized"), "{a} utilisée sans être initialisée"),
    (re.compile(r"'(?P<a>[^']+)' may be used uninitialized"), "{a} peut être utilisée sans être initialisée"),
    (re.compile(r"suggest parentheses around (?P<a>.*)"), "parenthèses conseillées autour de {a}"),
    (re.compile(r"this '(?P<a>[^']+)' clause does not guard.*"),
     "indentation trompeuse après {a} (accolades manquantes ?)"),
]


def _normalize_quotes(text: str) -> str:
    return text.replace("‘", "'").replace("’", "'").replace("`", "'")


def _short_path(path: str) -> str:
    """Les fichiers sont compilés dans un dossier temporaire : on ne garde que le nom."""
    return path.rsplit("/", 1)[-1] if path.startswith("/") else path


def _translate(msg: str) -> str:
    msg = _WERROR_RE.sub("", msg).strip()
    for pattern, fr in _TRANSLATIONS:
        m = pattern.search(msg)
        if m:
            return fr.format(**{k: v for k, v in m.groupdict().items() if v is not None})
    return msg


def summarize(output: str, limit: int = 8) -> List[str]:
    """Une ligne par erreur : « fichier:ligne  explication ». Liste vide si rien de reconnu."""
    text = _normalize_quotes(output)
    lines = text.splitlines()
    items: List[str] = []
    seen = set()

    for i, line in enumerate(lines):
        m = _DIAG_RE.match(line.strip())
        if m:
            kind = m.group("kind")
            if kind == "note":
                continue
            where = f"{_short_path(m.group('file'))}:{m.group('line')}"
            msg = m.group("msg")
            fr = _translate(msg)
            # Conflit de types : on cherche la note qui donne la déclaration d'origine.
            if msg.startswith("conflicting types"):
                have = re.search(r"; have '([^']+)'", msg)
                for nxt in lines[i + 1:i + 8]:
                    n = _DIAG_RE.match(nxt.strip())
                    if n and n.group("kind") == "note" and "previous declaration" in n.group("msg"):
                        typ = re.search(r"with type '([^']+)'", n.group("msg"))
                        fr += f" dans {_short_path(n.group('file'))}:{n.group('line')}"
                        if have and typ:
                            fr += f" (ici {have.group(1)}, là-bas {typ.group(1)})"
                        break
            item = f"{where}  {fr}"
            if kind == "warning":
                item += " (warning)"
        else:
            ld = _LD_RE.search(line)
            if not ld:
                continue
            item = f"{ld.group('name')} appelée mais définie nulle part (édition de liens)"
        if item not in seen:
            seen.add(item)
            items.append(item)

    if len(items) > limit:
        items = items[:limit] + [f"... et {len(items) - limit} autre(s)"]
    return items


def short(output: str, limit: int = 8, fallback_lines: int = 6) -> str:
    """Résumé texte ; si rien n'est reconnu, les dernières lignes brutes."""
    items = summarize(output, limit)
    if items:
        return "\n".join(items)
    raw = [l for l in output.strip().splitlines() if l.strip()]
    return "\n".join(raw[-fallback_lines:]) or "(aucune sortie)"


def first_error(output: str) -> Optional[str]:
    items = summarize(output, limit=1)
    return items[0] if items else None
