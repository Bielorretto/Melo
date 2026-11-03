"""Tests d'un projet du Common Core (ex. libft).

Un projet = projects/<nom>/project.yaml + un manifest.yaml par fonction.
En plus des tests de fonctions (lancés par core.runner en « mode librairie »),
on vérifie les règles du sujet : rendu, Makefile, header, symboles de la lib,
norminette et README.

Par défaut on teste comme la moulinette ; strict=True (--strict) ajoute des
vérifications plus sévères : échecs de malloc simulés, helpers static, make re.
"""

import atexit
import fnmatch
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

import yaml

from core import report
from core.cc_errors import short as short_cc_error
from core.report import GREEN, RED, RESET, YELLOW, counts, print_results
from core.runner import TestResult, load_manifest, run_test

PROJECT_FILE = "project.yaml"

# Symboles qu'un compilateur peut ajouter tout seul : jamais comptés comme « fonction utilisée ».
_COMPILER_SYMBOLS = {"_GLOBAL_OFFSET_TABLE_", "__stack_chk_fail", "__stack_chk_guard",
                     "_DYNAMIC", "__dso_handle"}
# gcc peut générer des appels à ces fonctions (initialisation de tableaux, copie de structures) :
# on ne les reproche à l'élève que s'il les appelle vraiment dans son code.
_IMPLICIT_LIBC = {"memset", "memcpy", "memmove"}


# --------------------------------------------------------------------------- outils


def load_project(project_dir: Path) -> dict:
    with open(project_dir / PROJECT_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _ok(name: str) -> TestResult:
    return TestResult(name, True, "OK")


def _ko(name: str, got: str, expected: str, inp: Optional[str] = None) -> TestResult:
    return TestResult(name, False, "KO", input=inp, got=got, expected=expected)


def _skip(name: str, why: str) -> TestResult:
    return TestResult(name, False, why, skipped=True)


def _check(name: str, problems: List[str], expected: str, inp: Optional[str] = None,
           limit: int = 15) -> TestResult:
    """OK si aucun problème, sinon KO avec la liste (tronquée) des problèmes."""
    if not problems:
        return _ok(name)
    shown = problems[:limit]
    if len(problems) > limit:
        shown.append(f"... et {len(problems) - limit} autre(s)")
    return _ko(name, "\n".join(shown), expected, inp)


def _sh(cmd: List[str], cwd: Path, timeout: int = 120,
        env: Optional[dict] = None) -> Tuple[Optional[int], str]:
    """Lance cmd, renvoie (code de retour ou None si timeout, stdout+stderr)."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env, errors="replace")
    except subprocess.TimeoutExpired:
        return None, f"timeout après {timeout}s"
    except FileNotFoundError as e:
        return 127, str(e)
    return proc.returncode, proc.stdout + proc.stderr


def _tail(text: str, n: int = 12) -> str:
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) > n:
        lines = ["...", *lines[-n:]]
    return "\n".join(lines) or "(aucune sortie)"


def _root_files(student_dir: Path, pattern: str) -> List[Path]:
    return sorted(p for p in student_dir.glob(pattern) if p.is_file())


def _student_files(student_dir: Path) -> Tuple[List[str], bool]:
    """Fichiers rendus (chemins relatifs). Dépôt git : fichiers suivis par git."""
    if (student_dir / ".git").exists():
        rc, out = _sh(["git", "ls-files"], student_dir, timeout=30)
        if rc == 0:
            return sorted(l for l in out.splitlines() if l.strip()), True
    files = []
    for p in student_dir.rglob("*"):
        rel = p.relative_to(student_dir)
        if p.is_file() and ".git" not in rel.parts and p.suffix not in (".o", ".a"):
            files.append(rel.as_posix())
    return sorted(files), False


def _nm(path: Path) -> List[Tuple[str, str]]:
    """[(type, nom)] des symboles d'un objet ou d'une archive."""
    rc, out = _sh(["nm", str(path)], path.parent, timeout=30)
    symbols = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 1:
            symbols.append((parts[0], parts[1]))
        elif len(parts) == 3 and len(parts[1]) == 1:
            symbols.append((parts[1], parts[2]))
    return symbols


def _prototypes(project: dict) -> Dict[str, List[str]]:
    protos = {}
    for name, cfg in project["functions"].items():
        p = cfg["prototype"]
        protos[name] = p if isinstance(p, list) else [p]
    return protos


# --------------------------------------------------------------------------- compilation de la lib


@dataclass
class LibraryBuild:
    """La lib de l'élève compilée par Melo (indépendamment de son Makefile)."""
    root: Path
    include_dir: Path
    archive: Optional[Path]
    objects: Dict[str, Path] = field(default_factory=dict)        # "ft_x.c" -> .o
    compile_errors: Dict[str, str] = field(default_factory=dict)  # "ft_x.c" -> erreur
    test_includes: Optional[Path] = None
    # Mode sans header (-h) : headers vus par les mains de test (libft.h de référence de Melo).
    test_include_dir: Optional[Path] = None
    no_header: bool = False
    needs_header: Dict[str, str] = field(default_factory=dict)    # "ft_x.c" -> raison
    noheader_errors: Dict[str, str] = field(default_factory=dict)  # "ft_x.c" -> erreur sans .h
    # Objets mis dans l'archive (en mode -h : versions compilées sans header quand c'est possible).
    lib_objects: Dict[str, Path] = field(default_factory=dict)

    def failure_hint(self) -> str:
        hints = []
        if self.compile_errors:
            names = ", ".join(sorted(self.compile_errors))
            hints.append(f"(ces fichiers ne compilent pas avec -Wall -Wextra -Werror : {names}"
                         " — voir la section rendu)")
        if self.noheader_errors:
            names = ", ".join(sorted(self.noheader_errors))
            hints.append(f"(ces fichiers ne compilent pas sans libft.h : {names})")
        return "\n".join(hints)


def _strip_c(code: str) -> str:
    """Code sans commentaires ni chaînes, pour chercher des identifiants."""
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    code = re.sub(r"//[^\n]*", " ", code)
    return re.sub(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', '""', code)


def needs_header(code: str, project: dict) -> Optional[str]:
    """Pourquoi ce .c a besoin du header du projet (None s'il doit compiler sans) :
    il utilise t_list, ou il appelle une fonction du sujet définie dans un autre fichier."""
    code = _strip_c(code)
    if re.search(r"\b(t_list|s_list)\b", code):
        return "utilise t_list"
    defined = set(re.findall(r"\b(\w+)\s*\([^;{)]*\)\s*\{", code))
    called = sorted({f for f in re.findall(r"\b(ft_\w+)\s*\(", code)
                     if f in project["functions"] and f not in defined})
    if called:
        return "appelle " + ", ".join(called)
    return None


def _reference_header(project: dict, dest: Path) -> None:
    """libft.h de référence de Melo : t_list + prototypes exacts du sujet."""
    guard = project["header"].upper().replace(".", "_")
    protos = "\n".join((p[0] if isinstance(p, list) else p) + ";"
                       for p in (cfg["prototype"] for cfg in project["functions"].values()))
    dest.write_text(
        f"#ifndef {guard}\n# define {guard}\n\n# include <stddef.h>\n# include <stdlib.h>\n"
        "# include <unistd.h>\n\ntypedef struct s_list\n{\n\tvoid\t\t\t*content;\n"
        f"\tstruct s_list\t*next;\n}}\tt_list;\n\n{protos}\n\n#endif\n", encoding="utf-8")


def build_library(project_dir: Path, project: dict, student_dir: Path,
                  no_header: bool = False) -> LibraryBuild:
    """Compile chaque .c de la racine séparément, puis crée l'archive avec ar.

    no_header=True (-h) : chaque .c qui n'a pas besoin du header (ni t_list, ni appel à une
    autre fonction du sujet) est compilé avec un libft.h vide, et c'est cet objet qui va dans
    la lib : la fonction doit se suffire à elle-même. Les mains de test utilisent alors le
    libft.h de référence de Melo au lieu de celui de l'élève."""
    root = Path(tempfile.mkdtemp(prefix="melo_lib_"))
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    src_dir, obj_dir = root / "src", root / "obj"
    src_dir.mkdir()
    obj_dir.mkdir()
    for p in [*_root_files(student_dir, "*.c"), *_root_files(student_dir, "*.h")]:
        shutil.copy(p, src_dir / p.name)

    cfg = project.get("compile", {})
    compiler = cfg.get("compiler", "cc")
    flags = cfg.get("flags", ["-Wall", "-Wextra", "-Werror"])
    includes = project_dir / "includes"
    build = LibraryBuild(root, src_dir, None,
                         test_includes=includes if includes.is_dir() else None,
                         no_header=no_header)

    def compile_one(src: Path) -> Tuple[str, Optional[str]]:
        obj = obj_dir / (src.stem + ".o")
        rc, out = _sh([compiler, *flags, "-I", str(src_dir), "-c", str(src), "-o", str(obj)],
                      src_dir, timeout=60)
        return src.name, None if rc == 0 else (out or f"code de retour {rc}")

    sources = sorted(src_dir.glob("*.c"))
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        for name, err in pool.map(compile_one, sources):
            if err is None:
                build.objects[name] = obj_dir / (Path(name).stem + ".o")
            else:
                build.compile_errors[name] = err.replace(str(src_dir) + "/", "")

    if no_header:
        ref_dir = root / "ref_include"
        ref_dir.mkdir()
        _reference_header(project, ref_dir / project["header"])
        build.test_include_dir = ref_dir
        noh_obj_dir = root / "obj_sans_header"
        noh_obj_dir.mkdir()

        def compile_without_header(src: Path) -> Tuple[str, Optional[str]]:
            # Dossier isolé : le .c, et un header vide à la place de celui de l'élève.
            work = root / "sans_header" / src.stem
            work.mkdir(parents=True)
            shutil.copy(src, work / src.name)
            (work / project["header"]).write_text("", encoding="utf-8")
            obj = noh_obj_dir / (src.stem + ".o")
            rc, out = _sh([compiler, *flags, "-I", str(work), "-c", src.name, "-o", str(obj)],
                          work, timeout=60)
            return src.name, None if rc == 0 else (out or f"code de retour {rc}")

        build.lib_objects = dict(build.objects)
        independent = []
        for src in sources:
            if src.name in build.compile_errors:
                continue
            why = needs_header(src.read_text(errors="replace"), project)
            if why:
                build.needs_header[src.name] = why
            else:
                independent.append(src)
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            for name, err in pool.map(compile_without_header, independent):
                if err is None:
                    build.lib_objects[name] = noh_obj_dir / (Path(name).stem + ".o")
                else:
                    build.lib_objects.pop(name, None)
                    build.noheader_errors[name] = err
    else:
        build.lib_objects = dict(build.objects)

    if build.lib_objects:
        archive = root / project.get("library", "lib.a")
        rc, _ = _sh(["ar", "rcs", str(archive), *map(str, build.lib_objects.values())], root)
        if rc == 0:
            build.archive = archive
    return build


# --------------------------------------------------------------------------- section rendu


def check_rendu(project: dict, student_dir: Path, build: LibraryBuild) -> List[TestResult]:
    results = []
    files, from_git = _student_files(student_dir)
    source = "fichiers suivis par git" if from_git else "fichiers du dossier"

    missing = [f for f in project["required_files"] if not (student_dir / f).is_file()]
    if not _root_files(student_dir, "ft_*.c"):
        missing.append("ft_*.c (aucun fichier source)")
    if from_git:
        missing += [f"{f} (présent mais pas commité)" for f in project["required_files"]
                    if (student_dir / f).is_file() and f not in files]
    results.append(_check("fichiers obligatoires présents (Makefile, libft.h, README.md, ft_*.c)",
                          [f"manquant : {m}" for m in missing], "tous présents à la racine"))

    nested = [f for f in files if "/" in f]
    results.append(_check("tous les fichiers sont à la racine du dépôt",
                          [f"pas à la racine : {f}" for f in nested],
                          "aucun sous-dossier", inp=source))

    allowed = project["allowed_files"]
    extra = [f for f in files if "/" not in f
             and not any(fnmatch.fnmatchcase(f, pat) for pat in allowed)]
    results.append(_check("aucun fichier en trop (fichiers inutiles interdits)",
                          [f"fichier non demandé : {f}" for f in extra],
                          "uniquement " + ", ".join(allowed), inp=source))

    errors = [err if report.VERBOSE else short_cc_error(err, limit=4)
              for _, err in sorted(build.compile_errors.items())]
    flags = " ".join(project.get("compile", {}).get("flags", []))
    results.append(_check(f"chaque .c compile avec cc {flags}", errors,
                          "aucune erreur ni warning", limit=5))

    restrict = []
    for p in [*_root_files(student_dir, "*.c"), *_root_files(student_dir, "*.h")]:
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if re.search(r"\b(__)?restrict(__)?\b", line):
                restrict.append(f"{p.name}:{i} : {line.strip()}")
    results.append(_check("pas de mot-clé restrict (interdit par le sujet)", restrict,
                          "aucun restrict dans les prototypes"))
    return results


# --------------------------------------------------------------------------- section Makefile


def _make_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("MAKEFLAGS", "MAKELEVEL", "MFLAGS")}
    env["LC_ALL"] = "C"
    return env


def _snapshot(work: Path) -> Dict[str, int]:
    return {p.relative_to(work).as_posix(): p.stat().st_mtime_ns
            for p in work.rglob("*") if p.is_file()}


def _objects(work: Path) -> List[str]:
    return sorted(p.relative_to(work).as_posix() for p in work.rglob("*.o"))


def _leftover_objects(work: Path) -> List[str]:
    objs = _objects(work)
    if not objs:
        return []
    shown = ", ".join(objs[:4]) + (", ..." if len(objs) > 4 else "")
    return [f"{len(objs)} fichier(s) .o restant(s) : {shown}"]


# Erreurs de make les plus courantes, expliquées.
_MAKE_ERRORS = [
    (re.compile(r"^(?P<w>\S+:\d+): \*\*\* missing separator"),
     "{w} : erreur de syntaxe, il manque une tabulation en début de commande (des espaces à la place ?)"),
    (re.compile(r"^(?P<w>\S+:\d+): \*\*\* multiple target patterns"),
     "{w} : erreur de syntaxe (« multiple target patterns » : souvent un « : » en trop ou une variable mal écrite)"),
    (re.compile(r"^(?P<w>\S+:\d+): \*\*\* (?P<m>.*?)\.?\s+Stop\."), "{w} : erreur de syntaxe ({m})"),
    (re.compile(r"No rule to make target '(?P<t>[^']+)', needed by '(?P<n>[^']+)'"),
     "fichier {t} introuvable (demandé par la règle {n})"),
    (re.compile(r"No rule to make target '(?P<t>[^']+)'"), "règle {t} absente"),
]


def _explain_make(out: str) -> Optional[str]:
    for line in out.replace("`", "'").replace("‘", "'").replace("’", "'").splitlines():
        line = re.sub(r"^make(\[\d+\])?: ", "", line.strip())
        for pattern, fr in _MAKE_ERRORS:
            m = pattern.search(line)
            if m:
                return fr.format(**m.groupdict())
    return None


def _make_failure(rc: Optional[int], out: str) -> str:
    """Message court pour un make qui échoue : l'explication si on la connaît, sinon la fin de la sortie."""
    explained = _explain_make(out)
    if explained:
        return f"make a échoué (code {rc}) : {explained}"
    errors = [l for l in out.splitlines() if re.search(r"error|\*\*\*", l)]
    if errors and not report.VERBOSE:
        detail = short_cc_error(out, limit=4) if any(": error:" in l for l in errors) else _tail("\n".join(errors), 4)
        return f"make a échoué (code {rc}) :\n{detail}"
    return f"make a échoué (code {rc}) :\n{_tail(out)}"


def check_makefile(project: dict, student_dir: Path, strict: bool = False) -> List[TestResult]:
    name = project["library"]
    rules = [*project["makefile_rules"], name]
    if not (student_dir / "Makefile").is_file():
        return [_ko("Makefile présent", "pas de fichier Makefile à la racine", "Makefile")]

    results: List[TestResult] = []
    env = _make_env()
    with tempfile.TemporaryDirectory(prefix="melo_make_") as tmp:
        work = Path(tmp) / "rendu"
        shutil.copytree(student_dir, work, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "*.o", "*.a"))

        def make(*args: str) -> Tuple[Optional[int], str]:
            return _sh(["make", *args], work, timeout=180, env=env)

        lib = work / name

        # 1. make construit la lib
        rc, out = make()
        if rc != 0:
            results.append(_ko(f"make crée {name} à la racine", _make_failure(rc, out),
                               f"{name} créé", inp="make"))
        elif not lib.is_file():
            built = [p.relative_to(work).as_posix() for p in work.rglob("*.a")]
            where = f" (trouvé : {', '.join(built)})" if built else ""
            results.append(_ko(f"make crée {name} à la racine", f"{name} absent de la racine{where}",
                               f"{name} créé à la racine", inp="make"))
        else:
            results.append(_ok(f"make crée {name} à la racine"))
        built_ok = rc == 0 and lib.is_file()

        # Makefile illisible par make : les autres vérifications n'ont pas de sens.
        p_rc, p_out = make("-n", "-p", "-q", "nothing_melo_target_xyz")
        if re.search(r"^\S+:\d+: \*\*\*", p_out, re.M):
            todo = "règles, commandes cc/ar, .c compilés, relink, contenu de la lib, clean, fclean"
            results.append(_skip(todo + (", re" if strict else ""),
                                 "non vérifiés : make ne peut pas lire le Makefile (erreur ci-dessus)"))
            return results

        # 2. règles obligatoires
        problems = []
        for rule in rules:
            r_rc, r_out = make("-n", rule)
            if r_rc != 0 or "No rule to make target" in r_out:
                problems.append(f"règle {rule} absente ou en erreur")
        _, db = make("-pn")
        m = re.search(r"^NAME\s*:?:?=\s*(.*?)\s*$", db, re.M)
        if not m:
            problems.append("variable NAME absente")
        elif m.group(1) != name:
            problems.append(f"NAME = {m.group(1)} (devrait être {name})")
        results.append(_check("règles $(NAME), all, clean, fclean et re présentes", problems,
                              f"NAME = {name} et les règles {', '.join(rules)}"))

        # 3. commandes : cc + flags, ar, pas de libtool
        _, dry = make("-n", "-B")
        compiled: Set[str] = set()
        problems = []
        # problème -> (nombre de commandes concernées, exemple de commande)
        grouped: Dict[str, List] = {}

        def note(problem: str, line: str) -> None:
            entry = grouped.setdefault(problem, [0, line.strip()])
            entry[0] += 1

        compile_lines, ar_lines = 0, 0
        for line in dry.splitlines():
            try:
                tokens = shlex.split(line)
            except ValueError:
                tokens = line.split()
            if not tokens:
                continue
            c_files = [t for t in tokens if t.endswith(".c")]
            compiled.update(Path(t).name for t in c_files)
            if "libtool" in line:
                note("libtool est interdit", line)
            if Path(tokens[0]).name == "ar":
                ar_lines += 1
            if c_files and "-c" in tokens:
                compile_lines += 1
                if Path(tokens[0]).name != "cc":
                    note(f"compilateur {tokens[0]} au lieu de cc", line)
                lacking = [f for f in project["compile"]["flags"] if f not in tokens]
                if lacking:
                    note(f"flags manquants : {' '.join(lacking)}", line)
                if any(t.startswith("-std=c99") for t in tokens):
                    note("-std=c99 est interdit", line)
        for problem, (count, example) in grouped.items():
            problems.append(f"{problem} ({count} commande(s), ex. : {example})")
        if compile_lines == 0:
            problems.append("aucune commande de compilation (cc ... -c fichier.c) détectée")
        if ar_lines == 0:
            problems.append("la lib n'est pas créée avec ar")
        flags = " ".join(project["compile"]["flags"])
        results.append(_check(f"compile avec cc {flags} et crée la lib avec ar",
                              list(dict.fromkeys(problems)),
                              f"cc {flags} -c ... puis ar ...", inp="make -n -B", limit=6))

        # 4. tous les .c sont compilés (fichiers inutiles interdits)
        unused = [p.name for p in _root_files(work, "*.c") if p.name not in compiled]
        results.append(_check("chaque .c rendu est compilé par le Makefile",
                              [f"jamais compilé : {f}" for f in unused],
                              "aucun fichier .c inutilisé", inp="make -n -B"))

        if not built_ok:
            for n in ("pas de relink", f"{name} contient toutes les fonctions du sujet",
                      "make clean", "make fclean", *(["make re"] if strict else [])):
                results.append(_skip(n, "nécessite que make fonctionne"))
            return results

        # 5. pas de relink
        before = _snapshot(work)
        make()
        make("all")
        after = _snapshot(work)
        changed = sorted(f for f in after if before.get(f) != after[f])
        results.append(_check("pas de relink (make relancé ne refait rien)",
                              [f"refait : {f}" for f in changed],
                              "aucun fichier recompilé ni relinké", inp="make && make && make all"))

        # 6. contenu de la lib produite par le Makefile
        defined = {n for t, n in _nm(lib) if t == "T"}
        missing = [f for f in project["functions"] if f not in defined]
        results.append(_check(f"{name} contient toutes les fonctions du sujet",
                              [f"absente : {f}" for f in missing],
                              f"les {len(project['functions'])} fonctions", inp=f"nm {name}"))

        # 7. clean
        rc, out = make("clean")
        problems = [] if rc == 0 else [_make_failure(rc, out).replace("make", "make clean", 1)]
        problems += _leftover_objects(work)
        if not lib.is_file():
            problems.append(f"{name} a été supprimé (clean ne doit supprimer que les .o)")
        results.append(_check("make clean supprime les .o et garde la lib", problems,
                              f"plus aucun .o, {name} toujours là", inp="make clean"))

        # 8. fclean (on reconstruit d'abord pour avoir des .o à supprimer)
        make()
        rc, out = make("fclean")
        problems = [] if rc == 0 else [_make_failure(rc, out).replace("make", "make fclean", 1)]
        problems += _leftover_objects(work)
        if lib.exists():
            problems.append(f"{name} toujours présent")
        results.append(_check("make fclean supprime les .o et la lib", problems,
                              f"plus aucun .o ni {name}", inp="make fclean"))

        # 9. re (non vérifié par la moulinette : mode --strict uniquement)
        if not strict:
            return results
        make()
        old = lib.stat().st_mtime_ns if lib.exists() else None
        rc, out = make("re")
        problems = []
        if rc != 0:
            problems.append(f"make re a échoué (code {rc}) :\n{_tail(out, 6)}")
        if not lib.is_file():
            problems.append(f"{name} absent après make re")
        elif old is not None and lib.stat().st_mtime_ns == old:
            problems.append(f"{name} n'a pas été recréé")
        circular = re.findall(r"^make: Circular .*$", out, re.M)
        problems += [f"message de make : {c}" for c in circular]
        results.append(_check("make re recompile tout", problems,
                              f"{name} supprimé puis recréé", inp="make && make re"))
    return results


# --------------------------------------------------------------------------- section header


def _syntax_check(code: str, build: LibraryBuild, project: dict) -> Tuple[bool, str]:
    cfg = project.get("compile", {})
    with tempfile.TemporaryDirectory(prefix="melo_h_") as tmp:
        src = Path(tmp) / "check.c"
        src.write_text(code, encoding="utf-8")
        rc, out = _sh([cfg.get("compiler", "cc"), *cfg.get("flags", []), "-fsyntax-only",
                       "-I", str(build.include_dir), str(src)], Path(tmp), timeout=30)
        return rc == 0, out.replace(str(src), "test.c")


def _student_prototype(header_text: str, func: str) -> Optional[str]:
    flat = re.sub(r"/\*.*?\*/", " ", header_text, flags=re.S)
    flat = re.sub(r"//[^\n]*", " ", flat)
    for decl in flat.split(";"):
        if re.search(rf"\b{func}\s*\(", decl):
            decl = decl.split("\n#")[-1] if "#" in decl else decl
            return re.sub(r"\s+", " ", decl).strip()
    return None


def check_header(project: dict, student_dir: Path, build: LibraryBuild) -> List[TestResult]:
    header = project["header"]
    if not (build.include_dir / header).is_file():
        return [_ko(f"{header} présent", f"{header} absent de la racine", f"{header} à la racine")]
    results = []
    inc = f'#include "{header}"\n'

    ok, out = _syntax_check(inc + "int main(void)\n{\n\treturn (0);\n}\n", build, project)
    results.append(_ok(f"{header} compile seul") if ok else
                   _ko(f"{header} compile seul", _tail(out), "aucune erreur (il inclut ce dont il a besoin)"))

    ok2, out2 = _syntax_check(inc + inc + "int main(void)\n{\n\treturn (0);\n}\n", build, project)
    if not ok:
        results.append(_skip("protégé contre la double inclusion", f"{header} ne compile pas seul"))
    else:
        results.append(_ok("protégé contre la double inclusion") if ok2 else
                       _ko("protégé contre la double inclusion", _tail(out2, 6),
                           "#ifndef / # define / #endif autour du header", inp=f"{header} inclus deux fois"))

    struct_code = inc + (
        "_Static_assert(__builtin_types_compatible_p(__typeof__(((t_list *)0)->content), void *),\n"
        "\t\"content doit etre un void *\");\n"
        "_Static_assert(__builtin_types_compatible_p(__typeof__(((t_list *)0)->next), struct s_list *),\n"
        "\t\"next doit etre un struct s_list *\");\n"
        "_Static_assert(sizeof(t_list) == 2 * sizeof(void *), \"t_list ne doit avoir que content et next\");\n"
        "int main(void)\n{\n\treturn (0);\n}\n")
    ok3, out3 = _syntax_check(struct_code, build, project)
    results.append(_ok("structure t_list conforme au sujet") if ok3 else
                   _ko("structure t_list conforme au sujet", _tail(out3, 6),
                       "typedef struct s_list { void *content; struct s_list *next; } t_list;"))

    header_text = (build.include_dir / header).read_text(errors="replace")

    def check_proto(item: Tuple[str, List[str]]) -> Optional[str]:
        func, protos = item
        for proto in protos:
            ref = re.sub(rf"\b{func}\b(?=\s*\()", f"melo_ref_{func}", proto, count=1)
            code = (inc + f"{ref};\n_Static_assert(__builtin_types_compatible_p("
                    f"__typeof__({func}), __typeof__(melo_ref_{func})), \"proto\");\n"
                    "int main(void)\n{\n\treturn (0);\n}\n")
            good, err = _syntax_check(code, build, project)
            if good:
                return None
            if not ok:
                return f"{func} : {header} ne compile pas"
        student = _student_prototype(header_text, func)
        if student is None:
            return f"{func} : absent de {header}"
        return f"{func} : « {student} » au lieu de « {' ou '.join(protos)} »"

    if not ok:
        results.append(_skip("prototypes conformes au sujet", f"{header} ne compile pas"))
    else:
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            problems = [p for p in pool.map(check_proto, _prototypes(project).items()) if p]
        results.append(_check("prototypes conformes au sujet", problems,
                              "les prototypes exacts du sujet", inp=header, limit=50))
    return results


# --------------------------------------------------------------------------- section symboles


def check_symbols(project: dict, student_dir: Path, build: LibraryBuild,
                  strict: bool = False) -> List[TestResult]:
    if not build.objects:
        return [_skip("symboles de la lib", "aucun fichier n'a compilé")]
    functions = project["functions"]
    per_obj = {src: _nm(obj) for src, obj in build.objects.items()}
    defined_everywhere = {n for syms in per_obj.values() for t, n in syms if t in "TW"}
    results = []

    missing = [f for f in functions if f not in defined_everywhere]
    if build.compile_errors:
        hint = f" (non compilés : {', '.join(sorted(build.compile_errors))})"
        missing = [m + hint for m in missing]
    results.append(_check("toutes les fonctions du sujet sont définies",
                          [f"absente : {m}" for m in missing],
                          f"les {len(functions)} fonctions du sujet"))

    globals_ = []
    for src, syms in sorted(per_obj.items()):
        for t, n in syms:
            if t in "BCDbd" and "." not in n:
                globals_.append(f"{src} : variable globale {n}")
    results.append(_check("aucune variable globale", globals_, "aucune variable globale"))

    helpers = []
    for src, syms in sorted(per_obj.items()):
        for t, n in syms:
            if t == "T" and n not in functions and n != Path(src).stem:
                helpers.append(f"{src} : {n} n'est pas static")
    if strict:
        results.append(_check("fonctions helpers déclarées en static", helpers,
                              "toute fonction hors sujet en static"))

    forbidden = []
    for src, syms in sorted(per_obj.items()):
        own = [n for t, n in syms if t == "T" and n in functions]
        allowed = set(project.get("default_allowed", [])) if not own else \
            {a for f in own for a in functions[f].get("allowed", [])}
        code = (build.include_dir / src).read_text(errors="replace")
        for t, n in syms:
            if (t != "U" or n in defined_everywhere or n in functions or n in allowed
                    or n in _COMPILER_SYMBOLS):
                continue
            if n in _IMPLICIT_LIBC and not re.search(rf"(?<![\w]){n}\s*\(", code):
                continue
            who = ", ".join(own) or src
            forbidden.append(f"{src} : {n} (autorisé pour {who} : {', '.join(sorted(allowed)) or 'rien'})")
    results.append(_check("seulement les fonctions externes autorisées", forbidden,
                          "malloc/free/write uniquement là où le sujet les autorise", inp="nm sur chaque .o"))
    return results


# --------------------------------------------------------------------------- section norme


def check_norm(project: dict, student_dir: Path) -> List[TestResult]:
    name = "norminette sur tous les .c et .h"
    if shutil.which("norminette") is None:
        return [_skip(name, "norminette n'est pas installée (pip install norminette)")]
    files = [p.name for p in [*_root_files(student_dir, "*.c"), *_root_files(student_dir, "*.h")]]
    if not files:
        return [_skip(name, "aucun fichier")]
    rc, out = _sh(["norminette", *files], student_dir, timeout=300)
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    if rc is None:
        return [_ko(name, out, "norminette OK sur chaque fichier")]
    problems, current = [], None
    for line in out.splitlines():
        m = re.match(r"^(\S+): Error!", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^\s*Error:\s*(\S+)\s*\(line:\s*(\d+), col:\s*(\d+)\):\s*(.*)$", line)
        if m:
            problems.append(f"{current}:{m.group(2)} {m.group(1)} — {m.group(4).strip()}")
        elif line.startswith("Error") or "Error:" in line:
            problems.append(f"{current or '?'} : {line.strip()}")
    if rc != 0 and not problems:
        problems.append(_tail(out, 6))
    return [_check(name, problems, "OK! pour chaque fichier", inp=f"norminette ({len(files)} fichiers)", limit=20)]


# --------------------------------------------------------------------------- section README


def check_readme(project: dict, student_dir: Path) -> List[TestResult]:
    readme = student_dir / "README.md"
    if not readme.is_file():
        return [_ko("README.md présent", "README.md absent de la racine", "README.md à la racine")]
    cfg = project["readme"]
    text = readme.read_text(errors="replace")
    lines = text.splitlines()
    results = []

    first = lines[0].strip() if lines else ""
    sentence = re.escape(cfg["first_line"])
    pattern = rf"^(\*|_){sentence} [\w.-]+(, [\w.-]+)*\.?\1$"
    results.append(_ok("première ligne en italique avec le(s) login(s)")
                   if re.match(pattern, first) and not first.startswith("**") else
                   _ko("première ligne en italique avec le(s) login(s)", json_line(first),
                       f"*{cfg['first_line']} <login1>[, <login2>...]*"))

    headings = [(len(m.group(1)), m.group(2).strip(), i)
                for i, l in enumerate(lines) if (m := re.match(r"^(#{1,6})\s+(.*)$", l))]
    missing = [s for s in cfg["sections"]
               if not any(re.search(rf"\b{s}\b", h, re.I) for _, h, _ in headings)]
    results.append(_check("sections " + ", ".join(cfg["sections"]) + " présentes",
                          [f"section manquante : {s}" for s in missing], "un titre # pour chacune"))

    res = [(lvl, i) for lvl, h, i in headings if re.search(r"\bResources?\b|\bRessources?\b", h, re.I)]
    if not res:
        results.append(_skip("utilisation de l'IA décrite dans Resources", "pas de section Resources"))
    else:
        lvl, start = res[0]
        end = next((i for l, _, i in headings if i > start and l <= lvl), len(lines))
        body = "\n".join(lines[start:end])
        ai = re.search(r"\b(AI|IA|intelligence artificielle|artificial intelligence|ChatGPT|LLM|Claude|Copilot)\b", body, re.I)
        results.append(_ok("utilisation de l'IA décrite dans Resources") if ai else
                       _ko("utilisation de l'IA décrite dans Resources", "aucune mention de l'IA dans Resources",
                           "pour quelles tâches et quelles parties l'IA a été utilisée"))
    return results


def json_line(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"' if s else "(ligne vide)"


# --------------------------------------------------------------------------- orchestration


def find_project(projects_root: Path, target: str) -> Optional[Tuple[Path, Optional[str]]]:
    parts = target.strip("/").split("/", 1)
    project_dir = projects_root / parts[0]
    if (project_dir / PROJECT_FILE).is_file():
        return project_dir, (parts[1] if len(parts) > 1 else None)
    return None


def detect_project(projects_root: Path, student_dir: Path) -> Optional[str]:
    for pf in sorted(projects_root.glob(f"*/{PROJECT_FILE}")):
        if (student_dir / load_project(pf.parent)["header"]).is_file():
            return pf.parent.name
    return None


def list_project_targets(projects_root: Path) -> List[str]:
    targets = []
    for pf in sorted(projects_root.glob(f"*/{PROJECT_FILE}")):
        name = pf.parent.name
        targets.append(name)
        targets += [f"{name}/{s}" for s in _CHECK_KEYS]
        targets += [f"{name}/{m.parent.name}" for m in _function_manifests(pf.parent, load_project(pf.parent))]
    return targets


_CHECK_KEYS = ["rendu", "makefile", "header", "symboles", "norme", "readme"]


def _function_manifests(project_dir: Path, project: dict) -> List[Path]:
    order = {name: i for i, name in enumerate(project["functions"])}
    found = list(project_dir.rglob("manifest.yaml"))
    return sorted(found, key=lambda p: (order.get(p.parent.name, len(order)), p.parent.name))


def run_project(project_dir: Path, student_dir: Path, only: Optional[str] = None,
                timeout: int = 5, strict: bool = False, no_header: bool = False,
                student_arg: Optional[str] = None) -> bool:
    """strict=False (défaut) : mode moulinette, les vérifications plus sévères que la
    moulinette (tests marqués strict, helpers static, make re) ne sont pas lancées."""
    project = load_project(project_dir)
    pname = project["name"]

    if not student_dir.is_dir():
        print(f"{RED}Dossier introuvable : {student_dir}{RESET}")
        return False
    if not _root_files(student_dir, "*.c") and not (student_dir / "Makefile").exists():
        print(f"{RED}Aucun .c ni Makefile dans {student_dir} : précise le dossier de ta {pname}.{RESET}")
        print(f"  ex. ./cli.py test {pname} ~/{pname}")
        return False

    mode = "strict (plus sévère que la moulinette)" if strict else "moulinette"
    if no_header:
        mode += f", fonctions compilées sans {project['header']} (-h)"
    print(f"Test de {pname} dans {student_dir} — mode {mode}")
    build = build_library(project_dir, project, student_dir, no_header=no_header)
    ok_files, ko_files = len(build.objects), len(build.compile_errors)
    msg = f"{ok_files} fichier(s) compilé(s)"
    if ko_files:
        msg += f", {RED}{ko_files} en erreur{RESET}"
    print(f"Compilation de la lib par Melo : {msg}")
    if no_header:
        alone = len(build.lib_objects) - len(build.needs_header)
        line = (f"Sans {project['header']} : {alone} fichier(s) compilé(s) seuls, "
                f"{len(build.needs_header)} utilisent le header (compilés avec)")
        if build.noheader_errors:
            line += f", {RED}{len(build.noheader_errors)} en erreur{RESET}"
        print(line)
    print()

    header = project["header"]
    checks: List[Tuple[str, str, Callable[[], List[TestResult]]]] = [
        ("rendu", f"{pname}/rendu", lambda: check_rendu(project, student_dir, build)),
        ("makefile", f"{pname}/Makefile", lambda: check_makefile(project, student_dir, strict)),
        ("header", f"{pname}/{header}", lambda: check_header(project, student_dir, build)),
        ("symboles", f"{pname}/symboles", lambda: check_symbols(project, student_dir, build, strict)),
        ("norme", f"{pname}/norme", lambda: check_norm(project, student_dir)),
        ("readme", f"{pname}/README", lambda: check_readme(project, student_dir)),
    ]

    def function_section(manifest_path: Path) -> Callable[[], List[TestResult]]:
        def run() -> List[TestResult]:
            exo_dir = manifest_path.parent
            manifest = load_manifest(exo_dir)
            func = exo_dir.name
            own = f"{func}.c"
            tests = [t for t in manifest["tests"] if strict or not t.get("strict")]
            not_run = f"{len(tests)} test(s) de {func} non lancé(s)"
            if own in build.compile_errors:
                return [TestResult(f"{own} ne compile pas", False, not_run,
                                   compile_error=build.compile_errors[own])]
            header = project["header"]
            if own in build.noheader_errors:
                return [TestResult(f"{own} ne compile pas sans {header}", False, not_run,
                                   compile_error=build.noheader_errors[own],
                                   rule=f"cette fonction n'utilise ni t_list ni une autre fonction "
                                        f"du sujet : son .c doit inclure lui-même ce dont il a besoin "
                                        f"(ex. <unistd.h> pour write, <stdlib.h> pour malloc/free, <stddef.h> pour size_t)")]
            results = []
            if no_header and (student_dir / own).is_file() and own not in build.needs_header:
                results.append(_ok(f"compile sans {header}"))
            func_rule = project["functions"].get(func, {}).get("rule")
            for t in tests:
                r = run_test(exo_dir, student_dir, t, manifest, timeout=timeout, library=build)
                if not r.passed and not r.skipped:
                    r.rule = t.get("rule") or func_rule
                results.append(r)
            return results
        return run

    # (titre, cible pour relancer la section seule, fonction)
    sections: List[Tuple[str, str, Callable[[], List[TestResult]]]] = []
    key = only.strip("/").lower() if only else None
    for k, title, fn in checks:
        if key is None or key in (k, title.split("/", 1)[1].lower()):
            sections.append((title, k, fn))
    for mp in _function_manifests(project_dir, project):
        rel = mp.parent.relative_to(project_dir).as_posix().lower()
        if key is None or key == mp.parent.name.lower() or rel == key or rel.startswith(key + "/"):
            sections.append((f"{pname}/{mp.parent.name}", mp.parent.name, function_section(mp)))

    if not sections:
        print(f"{RED}'{only}' introuvable dans {pname}.{RESET} Cibles possibles :")
        for t in list_project_targets(project_dir.parent):
            if t.startswith(pname + "/"):
                print(f"  - {t}")
        return False

    all_ok = True
    totals = {"passed": 0, "total": 0, "skipped": 0}
    failed: List[Tuple[str, str, List[TestResult]]] = []
    compact = len(sections) > 1
    with ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 4)) as pool:
        futures = [(title, target, pool.submit(fn)) for title, target, fn in sections]
        for title, target, fut in futures:
            try:
                results = fut.result()
            except Exception as e:  # un bug du testeur ne doit pas cacher les autres sections
                results = [TestResult("exécution de la section", False, f"erreur interne de Melo : {e!r}")]
            ok = print_results(title, results, compact=compact)
            sys.stdout.flush()
            all_ok = all_ok and ok
            if not ok:
                failed.append((title, target, results))
            passed, total, skipped = counts(results)
            totals["passed"] += passed
            totals["total"] += total
            totals["skipped"] += skipped

    color = GREEN if all_ok else RED
    print(f"\n{color}=== {pname} : {totals['passed']}/{totals['total']} tests réussis"
          f" sur {len(sections)} section(s) ==={RESET}")
    if totals["skipped"]:
        print(f"{YELLOW}{totals['skipped']} test(s) non exécuté(s){RESET}")
    if failed and len(sections) > 1:
        options = "".join([f" {shlex.quote(student_arg)}" if student_arg else "",
                           " --strict" if strict else "", " -h" if no_header else ""])
        print(f"\n{RED}Résumé : {len(failed)} section(s) en échec{RESET}")
        width = max(len(title.split("/", 1)[1]) for title, _, _ in failed)
        for title, target, results in failed:
            passed, total, _ = counts(results)
            first_ko = next(r for r in results if not r.passed and not r.skipped)
            print(f"  {RED}{title.split('/', 1)[1]:<{width}}{RESET}  {total - passed} KO"
                  f"  ({first_ko.name})")
            print(f"  {'':<{width}}  → ./cli.py test {pname}/{target}{options}")
    return all_ok
