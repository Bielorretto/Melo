
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MemoryReport:
    available: bool       
    clean: bool        
    definitely_lost: int
    indirectly_lost: int
    errors: int
    raw_output: str


def check_memory(binary_path: str, args: Optional[List[str]] = None,
                  stdin_data: str = "", timeout: int = 10) -> MemoryReport:
    args = args or []
    if shutil.which("valgrind") is None:
        return MemoryReport(False, True, 0, 0, 0, "valgrind non installé sur cette machine")

    cmd = [
        "valgrind",
        "--leak-check=full",
        "--error-exitcode=42",
        "--quiet",
        binary_path,
        *args,
    ]
    try:
        proc = subprocess.run(
            cmd, input=stdin_data, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return MemoryReport(True, False, -1, -1, -1, "valgrind: timeout")

    output = proc.stderr

    def _sum(pattern: str, text: str) -> int:
        return sum(int(m.replace(",", "")) for m in re.findall(pattern, text))

    # Avec --quiet, valgrind n'affiche pas le résumé "definitely lost: X bytes" :
    # on additionne les blocs perdus un par un, et on compte les erreurs.
    definitely_lost = _sum(r"([\d,]+) bytes in [\d,]+ blocks are definitely lost", output)
    indirectly_lost = _sum(r"([\d,]+) bytes in [\d,]+ blocks are indirectly lost", output)
    errors = len(re.findall(r"==\d+== (?:Invalid |Conditional jump|Use of uninitialised|Mismatched free|"
                            r"Source and destination overlap|Syscall param)", output))
    if proc.returncode == 42 and not (definitely_lost or indirectly_lost or errors):
        errors = 1

    clean = definitely_lost == 0 and indirectly_lost == 0 and errors == 0
    return MemoryReport(True, clean, definitely_lost, indirectly_lost, errors, output)
