"""Génère les manifests ft_printf de Melo à partir des cas du printfTester de Tripouille.

Usage : python3 gen_printf.py <printfTester/tests> <projects/ft_printf>

Chaque fichier de test du printfTester (c_test.cpp, minus_test.cpp...) devient une section
Melo ; ses cas sont regroupés par conversion (%c, %s, %d...) en un test Melo chacun.
Chaque cas compare ft_printf à printf (sortie et valeur de retour), comme le printfTester.
"""
import re
import sys
from pathlib import Path

# fichier du printfTester -> (dossier Melo, ordre, titre, bonus ?)
FILES = {
    "c_test.cpp": ("mandatory/c", 1, "%c", False),
    "s_test.cpp": ("mandatory/s", 2, "%s", False),
    "p_test.cpp": ("mandatory/p", 3, "%p", False),
    "d_test.cpp": ("mandatory/d", 4, "%d", False),
    "i_test.cpp": ("mandatory/i", 5, "%i", False),
    "u_test.cpp": ("mandatory/u", 6, "%u", False),
    "x_test.cpp": ("mandatory/x", 7, "%x", False),
    "upperx_test.cpp": ("mandatory/upperx", 8, "%X", False),
    "percent_test.cpp": ("mandatory/percent", 9, "%%", False),
    "mix_test.cpp": ("mandatory/mix", 10, "mélange de conversions", False),
    "minus_test.cpp": ("bonus/minus", 11, "flag '-'", True),
    "0_test.cpp": ("bonus/zero", 12, "flag '0'", True),
    "dot_test.cpp": ("bonus/dot", 13, "précision '.'", True),
    "sharp_test.cpp": ("bonus/sharp", 14, "flag '#'", True),
    "space_test.cpp": ("bonus/space", 15, "flag ' '", True),
    "+_test.cpp": ("bonus/plus", 16, "flag '+'", True),
}

SPEC_RE = re.compile(r"%([-0# +]*)(\d*)(\.\d*)?([cspdiuxX%])")
TEST_RE = re.compile(r"TEST\(\s*\d+\s*,\s*print\((.*)\)\);\s*$")

CASTS = {
    "c": "(int)({})",
    "s": "(char *)({})",
    "p": "(void *)(uintptr_t)({})",
    "d": "(int)({})",
    "i": "(int)({})",
    "u": "(unsigned int)({})",
    "x": "(unsigned int)({})",
    "X": "(unsigned int)({})",
}

CONV_NAMES = {"c": "%c", "s": "%s", "p": "%p", "d": "%d", "i": "%i", "u": "%u",
              "x": "%x", "X": "%X", "%": "%%"}


def split_args(text: str) -> list:
    """Sépare les arguments au premier niveau (virgules hors chaînes et parenthèses)."""
    args, depth, cur, in_str, esc = [], 0, "", False, False
    for ch in text:
        if in_str:
            cur += ch
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def c_case(args: list) -> tuple:
    """(texte affiché, arguments C castés, conversion principale)"""
    fmt = args[0]
    specs = [m.group(4) for m in SPEC_RE.finditer(fmt) if m.group(4) != "%"]
    rest = args[1:]
    if len(specs) != len(rest):
        raise ValueError(f"{fmt} : {len(specs)} conversions pour {len(rest)} arguments")
    shown = ", ".join(args)
    casted = [CASTS[conv].format(a) for conv, a in zip(specs, rest)]
    main = specs[0] if specs else "%"
    return shown, [fmt, *casted], main


def c_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_block(text: str, indent: int) -> str:
    pad = " " * indent
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def generate(src: Path, dest_root: Path, filename: str) -> None:
    folder, order, title, bonus = FILES[filename]
    text = src.read_text(encoding="utf-8")
    variables = dict(re.findall(r"char\s*\*\s*(\w+)\s*=\s*(\"[^\"]*\")\s*;", text))
    groups = {}  # conversion -> [(shown, c_args)]
    for line in text.splitlines():
        m = TEST_RE.search(line)
        if not m:
            continue
        shown, c_args, conv = c_case(split_args(m.group(1)))
        groups.setdefault(conv, []).append((shown, c_args))

    lines = [
        f"# Généré par tools/gen_printf.py à partir du printfTester de Tripouille",
        f"# (github.com/Tripouille/printfTester, tests/{filename}).",
        f"# Chaque cas compare ft_printf à printf : même sortie, même valeur de retour.",
        f"name: {Path(folder).name}",
        f"order: {order}",
        f"build: {'bonus' if bonus else 'mandatory'}",
    ]
    if bonus:
        lines.append("bonus: true")
    rule = (f"sujet (bonus) : {title} doit se comporter comme dans printf"
            if bonus else f"sujet : {title} doit afficher la même chose que printf et renvoyer le nombre de caractères écrits")
    lines += [
        f"rule: \"{rule}\"",
        "compile:",
        "  # Les cas reprennent volontairement des formats que gcc signale (ex. '% s').",
        "  test_flags: [-Wno-format]",
        "prelude: |",
        "  #include \"melo_printf.h\"",
    ]
    for name, value in variables.items():
        lines.append(f"  static char *{name} = {value};")
    lines += [
        "test_defaults:",
        "  expected_exit: 0",
        "  check_memory: true",
        "tests:",
    ]
    for conv, cases in groups.items():
        conv_name = CONV_NAMES[conv]
        if filename == "mix_test.cpp":
            name = "toutes les conversions dans un même format"
        elif bonus:
            name = f"{title} avec {conv_name} ({len(cases)} cas)"
        else:
            name = f"{conv_name} ({len(cases)} cas du printfTester)"
        body = []
        for shown, c_args in cases:
            body.append(f"PF({c_string(shown)}, {', '.join(c_args)});")
        body.append("PF_DONE();")
        lines += [
            f"- name: {yaml_quote(name)}",
            f"  input: {yaml_quote(f'{len(cases)} appels ft_printf comparés à printf, ex. ft_printf({cases[0][0]})')}",
            "  body: |",
            yaml_block("\n".join(body), 4),
        ]
    out = dest_root / folder / "manifest.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out} : {sum(len(c) for c in groups.values())} cas, {len(groups)} test(s)")


def yaml_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main() -> None:
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    for filename in FILES:
        generate(src / filename, dest, filename)


if __name__ == "__main__":
    main()
