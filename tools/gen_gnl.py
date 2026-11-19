"""Génère les manifests get_next_line de Melo (cas du gnlTester de Tripouille).

Usage : python3 tools/gen_gnl.py projects/get_next_line

Les lignes attendues sont lues dans projects/get_next_line/files/ (mêmes fichiers que
github.com/Tripouille/gnlTester). Chaque fichier devient un test : get_next_line est appelé
jusqu'à NULL, et chaque ligne est comparée. Les grosses lignes sont construites par
melo_digits() au lieu d'être écrites en entier dans le manifest.
"""
import json
import sys
from pathlib import Path

# Ordre et noms des tests (comme le gnlTester).
FILES = [
    ("empty", "fichier vide"),
    ("nl", "un seul \\n"),
    ("41_no_nl", "41 caractères sans \\n final"),
    ("41_with_nl", "41 caractères avec \\n, puis 1 caractère"),
    ("42_no_nl", "42 caractères sans \\n final"),
    ("42_with_nl", "42 caractères avec \\n, puis 1 caractère"),
    ("43_no_nl", "43 caractères sans \\n final"),
    ("43_with_nl", "43 caractères avec \\n, puis 1 caractère"),
    ("multiple_nlx5", "5 lignes vides"),
    ("multiple_line_no_nl", "plusieurs lignes, sans \\n final"),
    ("multiple_line_with_nl", "plusieurs lignes, avec \\n final"),
    ("alternate_line_nl_no_nl", "lignes et lignes vides alternées, sans \\n final"),
    ("alternate_line_nl_with_nl", "lignes et lignes vides alternées, avec \\n final"),
    ("big_line_no_nl", "une ligne de 10000 caractères sans \\n"),
    ("big_line_with_nl", "une ligne de 10000 caractères avec \\n"),
]

BUILDS_MANDATORY = ["bs1", "bs42", "bs10M", "bonus_bs1", "bonus_bs42", "bonus_bs10M"]
BUILDS_BONUS = ["bonus_bs1", "bonus_bs42", "bonus_bs10M"]


def c_str(s: str) -> str:
    return json.dumps(s)  # une chaîne JSON ASCII est une chaîne C valide ici


def is_digits(line: str) -> bool:
    body = line.rstrip("\n")
    return len(body) > 100 and body == "".join(str(i % 10) for i in range(len(body)))


def indent(lines: list, n: int = 4) -> str:
    return "\n".join(" " * n + l if l else "" for l in lines)


def file_test(name: str, title: str, files: Path) -> str:
    data = (files / name).read_text()
    lines = data.splitlines(keepends=True)
    path = f"files/{name}"
    body = [f'int fd = open("{path}", O_RDONLY);', f'const char *w = "{path}";']
    frees = []
    for i, line in enumerate(lines):
        if is_digits(line):
            var = f"big{i}"
            body.append(f"char *{var} = melo_digits({len(line.rstrip(chr(10)))}, {int(line.endswith(chr(10)))});")
            body.append(f"GNL(fd, {var}, w);")
            frees.append(var)
        elif name == "42_with_nl" and i == 1:
            # Comme le gnlTester : avec BUFFER_SIZE=42, la 1re lecture prend exactement la
            # 1re ligne ; get_next_line ne doit pas avoir lu plus loin.
            body += [
                "#if BUFFER_SIZE == 42",
                "char c = 0;",
                "if (read(fd, &c, 1) != 1 || c != '1')",
                "{",
                '    printf("obtenu : le caractère suivant a déjà été lu par get_next_line\\n");',
                '    printf("attendu : avec BUFFER_SIZE=42, read(fd) renvoie encore \'1\' après la 1re ligne\\n");',
                "    return (1);",
                "}",
                "#else",
                f"GNL(fd, {c_str(line)}, w);",
                "#endif",
            ]
        else:
            body.append(f"GNL(fd, {c_str(line)}, w);")
    body.append("GNL(fd, NULL, w);")
    body += [f"free({v});" for v in frees]
    body.append("close(fd);")
    return "\n".join([
        f"- name: '{path} : {title}'",
        f"  input: get_next_line(fd) jusqu'à NULL sur {path} ({len(lines)} ligne(s))",
        "  body: |",
        indent(body),
    ])


def mandatory(files: Path) -> str:
    out = [
        "# Généré par tools/gen_gnl.py : cas du gnlTester de Tripouille",
        "# (github.com/Tripouille/gnlTester, tests/mandatory.cpp).",
        "# Lancé avec BUFFER_SIZE = 1, 42 et 10000000, sur les fichiers obligatoires puis bonus.",
        "name: mandatory",
        "order: 1",
        "builds: [" + ", ".join(BUILDS_MANDATORY) + "]",
        "files_dir: ../files",
        "rule: 'sujet : chaque appel renvoie la ligne suivante, \\n compris s''il y en a un ; NULL à la fin du fichier ou en cas d''erreur'",
        "prelude: |",
        '  #include "melo_gnl.h"',
        "test_defaults:",
        "  expected_exit: 0",
        "  check_memory: true",
        "  # Un gnl correct mais lent (BUFFER_SIZE=1, ligne de 10000 caractères) ne doit pas être KO :\n"
        "  # 30 s (60 s sous valgrind) ne sont dépassées que par une boucle infinie.",
        "  timeout: 30",
        "tests:",
        "- name: 'fd invalide (1000, -1, fd fermé) : NULL'",
        "  input: get_next_line(1000), get_next_line(-1), puis get_next_line sur un fd fermé",
        "  body: |",
        indent([
            "GNL(1000, NULL, \"1000\");",
            "GNL(-1, NULL, \"-1\");",
            'int fd = open("files/empty", O_RDONLY);',
            "close(fd);",
            'GNL(fd, NULL, "fd fermé");',
        ]),
    ]
    for name, title in FILES:
        out.append(file_test(name, title, files))
    stdin_data = (files / "alternate_line_nl_with_nl").read_text()
    lines = stdin_data.splitlines(keepends=True)
    out += [
        "- name: 'stdin (fd 0)'",
        "  input: get_next_line(0) jusqu'à NULL, avec files/alternate_line_nl_with_nl sur l'entrée standard",
        f"  stdin: {c_str(stdin_data)}",
        "  body: |",
        indent([f'GNL(0, {c_str(l)}, "0");' for l in lines] + ['GNL(0, NULL, "0");']),
    ]
    return "\n".join(out) + "\n"


def bonus() -> str:
    calls = [
        ('1000', 'NULL'), ('fd[0]', '"0123456789012345678901234567890123456789\\n"'),
        ('1001', 'NULL'), ('fd[1]', '"01234567890123456789012345678901234567890\\n"'),
        ('1002', 'NULL'), ('fd[2]', '"012345678901234567890123456789012345678901\\n"'),
        ('1003', 'NULL'), ('fd[0]', '"0"'),
        ('1004', 'NULL'), ('fd[1]', '"1"'),
        ('1005', 'NULL'), ('fd[2]', '"2"'),
        ('fd[0]', 'NULL'), ('fd[1]', 'NULL'), ('fd[2]', 'NULL'),
    ]
    body = [
        "int fd[4];",
        'fd[0] = open("files/41_with_nl", O_RDONLY);',
        'fd[1] = open("files/42_with_nl", O_RDONLY);',
        'fd[2] = open("files/43_with_nl", O_RDONLY);',
    ]
    body += [f'GNL({fd}, {exp}, "{fd}");' for fd, exp in calls]
    body += [
        'fd[3] = open("files/nl", O_RDONLY);',
        'GNL(1006, NULL, "1006");',
        'GNL(fd[3], "\\n", "fd[3]");',
        'GNL(1007, NULL, "1007");',
        'GNL(fd[3], NULL, "fd[3]");',
        "for (int i = 0; i < 4; i++)",
        "    close(fd[i]);",
    ]
    return "\n".join([
        "# Généré par tools/gen_gnl.py : cas du gnlTester de Tripouille",
        "# (github.com/Tripouille/gnlTester, tests/bonus.cpp).",
        "name: bonus",
        "order: 2",
        "bonus: true",
        "builds: [" + ", ".join(BUILDS_BONUS) + "]",
        "files_dir: ../files",
        'rule: "sujet (bonus) : get_next_line gère plusieurs fd à la fois sans perdre la lecture de chacun"',
        "prelude: |",
        '  #include "melo_gnl.h"',
        "test_defaults:",
        "  expected_exit: 0",
        "  check_memory: true",
        "  # Un gnl correct mais lent (BUFFER_SIZE=1, ligne de 10000 caractères) ne doit pas être KO :\n"
        "  # 30 s (60 s sous valgrind) ne sont dépassées que par une boucle infinie.",
        "  timeout: 30",
        "tests:",
        "- name: plusieurs fd lus en alternance (avec des fd invalides entre les deux)",
        "  input: 3 fichiers ouverts, lus une ligne à la fois chacun, avec get_next_line(1000...) entre",
        "  body: |",
        indent(body),
    ]) + "\n"


def main() -> None:
    root = Path(sys.argv[1])
    files = root / "files"
    (root / "mandatory" / "manifest.yaml").write_text(mandatory(files), encoding="utf-8")
    (root / "bonus" / "manifest.yaml").write_text(bonus(), encoding="utf-8")
    print("manifests get_next_line générés")


if __name__ == "__main__":
    main()
