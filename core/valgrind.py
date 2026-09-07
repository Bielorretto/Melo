
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

    def _extract(pattern: str, text: str) -> int:
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else 0

    definitely_lost = _extract(r"definitely lost:\s*([\d,]+) bytes", output)
    indirectly_lost = _extract(r"indirectly lost:\s*([\d,]+) bytes", output)
    errors = _extract(r"ERROR SUMMARY:\s*([\d,]+) errors", output)

    clean = definitely_lost == 0 and indirectly_lost == 0 and errors == 0
    return MemoryReport(True, clean, definitely_lost, indirectly_lost, errors, output)
