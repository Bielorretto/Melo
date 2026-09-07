
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from openai import OpenAI

from ai.tools import (
    DEBUG_TOOLS_SCHEMA,
    EXERCISE_TOOLS_SCHEMA,
    get_exercise_subject,
    list_exercise_names,
    run_gdb_session,
)

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


class Assistant:
    def __init__(self):
        config = _load_config()
        api_key_env = config["openai"]["api_key_env"]
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(
                f"variable d'environnement {api_key_env} non définie "
                f"(export {api_key_env}=sk-...)"
            )
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = config["openai"]["model"]

    def _dispatch_tool(self, tool_call) -> str:
        """Exécute l'outil demandé par le modèle et renvoie le résultat texte."""
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")

        if name == "run_gdb_session":
            return run_gdb_session(args["binary_path"], args["commands"])
        if name == "list_exercises":
            names = list_exercise_names()
            return ", ".join(names) if names else "Aucun exercice trouvé."
        if name == "get_exercise_subject":
            return get_exercise_subject(args["exercise_name"])

        return f"Outil inconnu : {name}"

    def _run_completion(self, messages: list, tools: list | None = None) -> str:
        for _ in range(5):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                messages.append({"role": "assistant", "content": message.content})
                return message.content

            messages.append(message)
            for tool_call in message.tool_calls:
                result = self._dispatch_tool(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "L'assistant a dépassé le nombre d'appels d'outils autorisés."

    def ask(self, system_prompt: str, user_message: str, use_tools: bool = False) -> str:
        """Un seul aller-retour, sans mémoire (utilisé par ai-explain / ai-debug).
        use_tools=True donne accès à gdb (mode debug historique).
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        tools = DEBUG_TOOLS_SCHEMA if use_tools else None
        return self._run_completion(messages, tools)

    def start_chat(self, system_prompt: str) -> None:
        """Démarre une nouvelle conversation avec mémoire (utilisé par `chat`)."""
        self.messages = [{"role": "system", "content": system_prompt}]

    def send(self, user_message: str, use_tools: bool = False) -> str:
        """Envoie un message dans la conversation en cours (démarrée via
        start_chat) et renvoie la réponse, en gardant tout l'historique.

        Les outils "exercices" (list_exercises, get_exercise_subject) sont
        toujours disponibles en chat, pour que l'IA aille lire elle-même le
        bon sujet. use_tools=True ajoute en plus l'outil gdb (mode debug).
        """
        if not hasattr(self, "messages"):
            raise RuntimeError("start_chat() doit être appelé avant send()")

        tools = list(EXERCISE_TOOLS_SCHEMA)
        if use_tools:
            tools += DEBUG_TOOLS_SCHEMA

        self.messages.append({"role": "user", "content": user_message})
        return self._run_completion(self.messages, tools)