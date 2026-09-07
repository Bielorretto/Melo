
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    returncode: Optional[int]
    timed_out: bool


def run_binary(binary_path: str, args: Optional[List[str]] = None,
                stdin_data: str = "", timeout: int = 5) -> ExecResult:
    args = args or []
    try:
        proc = subprocess.run(
            [binary_path, *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ExecResult(proc.stdout, proc.stderr, proc.returncode, timed_out=False)
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors="replace")
        return ExecResult(stdout, stderr, None, timed_out=True)
