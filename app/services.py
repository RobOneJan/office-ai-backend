import os
import json
from google.cloud import secretmanager
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# Minimal in-memory ChatSessions für jede conversation_id
CHATS = {}
VERTEX_MODEL = None

# Preise pro Token (gemini-2.5-flash, Stand 2025)
PRICES = {
    "gemini-2.5-flash": {"input": 0.035 / 1000, "output": 0.07 / 1000}
}


def _get_secret(secret_path: str) -> str:
    """
    Lädt Secret aus GCP Secret Manager.
    secret_path = "projects/.../secrets/.../versions/latest"
    """
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_path)
    return response.payload.data.decode("utf-8")


def _init_vertexai():
    global VERTEX_MODEL
    if VERTEX_MODEL:
        return VERTEX_MODEL

    creds = None
    # Environment Variable kann JSON oder Pfad sein
    json_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if json_env:
        if os.path.exists(json_env):
            creds = service_account.Credentials.from_service_account_file(json_env)
        else:
            creds = service_account.Credentials.from_service_account_info(json.loads(json_env))
    elif os.path.exists("officeai-sa.json"):
        creds = service_account.Credentials.from_service_account_file("officeai-sa.json")
    else:
        # Optional: Secret Manager direkt nutzen
        if os.environ.get("GCP_SECRET_JSON"):
            key_json = _get_secret(os.environ["GCP_SECRET_JSON"])
            creds = service_account.Credentials.from_service_account_info(json.loads(key_json))
        else:
            raise ValueError("Keine Credentials gefunden. Lege officeai-sa.json ins Repo oder setze GOOGLE_APPLICATION_CREDENTIALS.")

    vertexai.init(
        project=os.environ.get("GCP_PROJECT", "dev-truth-471209-h0"),
        location="europe-west4",
        credentials=creds
    )

    VERTEX_MODEL = GenerativeModel("gemini-2.5-flash")
    return VERTEX_MODEL


def call_vertexai(conversation_id: str, message: str):
    """
    Führt ChatSession aus und liefert bot_message, Tokenverbrauch und Kosten.
    """
    model = _init_vertexai()

    # Session für conversation_id anlegen
    if conversation_id not in CHATS:
        CHATS[conversation_id] = {
            "chat": model.start_chat(),
            "messages": [],
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        }
    chat_data = CHATS[conversation_id]
    chat_data["messages"].append(("user", message))

    full_response = ""
    final_response = None
    for chunk in chat_data["chat"].send_message(message, stream=True):
        if chunk.text:
            full_response += chunk.text
        final_response = chunk

    chat_data["messages"].append(("assistant", full_response))

    # Token usage auswerten
    if final_response and final_response.usage_metadata:
        usage = final_response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        cost = (input_tokens * PRICES["gemini-2.5-flash"]["input"] +
                output_tokens * PRICES["gemini-2.5-flash"]["output"])
        chat_data["usage"]["input_tokens"] += input_tokens
        chat_data["usage"]["output_tokens"] += output_tokens
        chat_data["usage"]["cost"] += cost
    else:
        input_tokens = output_tokens = cost = 0

    return {
        "bot_message": full_response,
        "input_tokens": chat_data["usage"]["input_tokens"],
        "output_tokens": chat_data["usage"]["output_tokens"],
        "cost_usd": round(chat_data["usage"]["cost"], 6)
    }
