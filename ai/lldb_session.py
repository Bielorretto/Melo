
import os
import pty
import re
import select
import subprocess
import time
from typing import Optional


class LldbSession:
    """Session lldb persistante pilotee via un pty (pas un pipe simple : le
    prompt "(lldb) " ne se termine pas par un retour a la ligne, un pipe classique
    bloquerait indefiniment sur readline())."""

    def __init__(self, binary_path: str, timeout: float = 10.0):
        self.binary_path = binary_path
        self.timeout = timeout
        self._started = False
        self._goto_breakpoint_id: Optional[int] = None

        self._master, slave = pty.openpty()
        self._proc = subprocess.Popen(
            ["lldb", "-f", binary_path],
            stdin=slave, stdout=slave, stderr=slave,
            close_fds=True,
        )
        os.close(slave)
        self._read_until_prompt()

    def _read_until_prompt(self) -> str:
        buf = b""
        end = time.time() + self.timeout
        while time.time() < end:
            r, _, _ = select.select([self._master], [], [], 0.2)
            if self._master in r:
                try:
                    chunk = os.read(self._master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                if buf.rstrip().endswith(b"(lldb)"):
                    break
        return buf.decode(errors="replace")

    def _send(self, cmd: str) -> str:
        os.write(self._master, (cmd + "\n").encode())
        output = self._read_until_prompt()
        lines = output.splitlines()
        if lines and lines[0].strip() == cmd.strip():
            lines = lines[1:]
        if lines and lines[-1].strip() == "(lldb)":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _break_and_run(self, bp_cmd: str, target_desc: str) -> str:
        """Pose un breakpoint (par nom de fonction ou fichier:ligne) et (re)lance
        le programme jusqu'a ce point. Relance systematiquement depuis zero :
        lldb ne permet pas de revenir en arriere, donc c'est la seule facon
        fiable de garantir qu'on atteint la cible demandee, meme si elle a deja
        ete depassee."""
        if self._goto_breakpoint_id is not None:
            self._send(f"breakpoint delete {self._goto_breakpoint_id}")

        bp_output = self._send(bp_cmd)
        match = re.search(r"Breakpoint (\d+):", bp_output)
        self._goto_breakpoint_id = int(match.group(1)) if match else None

        if not match:
            return f"Impossible de poser un breakpoint sur {target_desc} :\n{bp_output}"

        if self._started:
            self._send("process kill")
        run_output = self._send("run")
        self._started = True
        return run_output

    def start_at_main(self) -> str:
        """Lance le programme et l'arrete des le debut de main(), comportement
        par defaut quand rien de precis n'a encore ete demande."""
        return self._break_and_run("b main", "main")

    def goto_line(self, file: str, line: int) -> str:
        """Amene l'execution jusqu'a file:line, peu importe la position actuelle."""
        return self._break_and_run(f"b {file}:{line}", f"{file}:{line}")

    def goto_function(self, function: str) -> str:
        """Amene l'execution au debut d'une fonction par son nom (ex: 'ft_split'),
        quel que soit le fichier ou elle est definie. Equivalent a "rentrer dans"
        cette fonction sans avoir a compter des next/step."""
        return self._break_and_run(f"b {function}", function)

    def print_variable(self, name: str) -> str:
        return self._send(f"print {name}")

    def list_variables(self) -> str:
        return self._send("frame variable")

    def show_source(self, file: str, line: int = 1, count: int = 200) -> str:
        """Affiche une portion du code source (par defaut, jusqu'a 200 lignes a
        partir du debut du fichier, ce qui couvre un fichier entier pour la
        plupart des exercices de piscine)."""
        return self._send(f"source list -f {file} -l {line} -c {count}")

    def close(self) -> None:
        try:
            self._send("quit")
        except Exception:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        try:
            os.close(self._master)
        except OSError:
            pass
