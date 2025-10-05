import os
import json
from google.cloud import secretmanager, dlp_v2
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Tenant, User, Conversation, Message, Embedding

# Minimal in-memory ChatSessions (für Token-Tracking)
CHATS = {}
VERTEX_MODEL = None

# Preise pro Token
PRICES = {
    "gemini-2.5-flash": {"input": 0.3 / 1000000, "output": 2.5 / 1000000}
}

# --- Secret Handling ---
def _get_secret(secret_path: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_path)
    return response.payload.data.decode("utf-8")

# --- Vertex Init ---
def _init_vertexai():
    global VERTEX_MODEL
    if VERTEX_MODEL:
        return VERTEX_MODEL

    creds = None
    json_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if json_env:
        if os.path.exists(json_env):
            creds = service_account.Credentials.from_service_account_file(json_env)
        else:
            creds = service_account.Credentials.from_service_account_info(json.loads(json_env))
    elif os.path.exists("officeai-sa.json"):
        creds = service_account.Credentials.from_service_account_file("officeai-sa.json")
    elif os.environ.get("GCP_SECRET_JSON"):
        key_json = _get_secret(os.environ["GCP_SECRET_JSON"])
        creds = service_account.Credentials.from_service_account_info(json.loads(key_json))
    else:
        raise ValueError("Keine Credentials gefunden.")

    vertexai.init(
        project=os.environ.get("GCP_PROJECT", "dev-truth-471209-h0"),
        location="europe-west4",
        credentials=creds
    )
    VERTEX_MODEL = GenerativeModel("gemini-2.5-flash")
    return VERTEX_MODEL

# --- DLP Masking ---
def mask_with_dlp(text: str):
    dlp = dlp_v2.DlpServiceClient()
    parent = f"projects/{os.environ.get('GCP_PROJECT', 'dev-truth-471209-h0')}/locations/europe-west3"
    item = {"value": text}

    inspect_config = {
        "info_types": [
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "PERSON_NAME"},
            {"name": "IBAN_CODE"},
        ],
        "include_quote": True
    }

    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {"primitive_transformation": {"replace_with_info_type_config": {}}}
            ]
        }
    }

    response = dlp.deidentify_content(
        request={"parent": parent, "inspect_config": inspect_config,
                 "deidentify_config": deidentify_config, "item": item}
    )

    mapping = {}
    if response.item and response.item.value != text:
        findings = dlp.inspect_content(
            request={"parent": parent, "inspect_config": inspect_config, "item": item}
        ).result.findings
        for finding in findings:
            mapping[f"<{finding.info_type.name}>"] = finding.quote

    return response.item.value, mapping

def restore_placeholders(text: str, mapping: dict):
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text

def call_vertexai(conversation_id: str, user_id: int, tenant_id: int, message: str):
    model = _init_vertexai()
    masked_message, mapping = mask_with_dlp(message)

    db: Session = SessionLocal()
    try:
        # --- Conversation finden oder anlegen ---
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            conversation = Conversation(id=conversation_id, user_id=user_id, tenant_id=tenant_id)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        conversation_id_value = conversation.id  # 👈 wichtig: speichern, bevor Session evtl. zu ist

        # --- Eingehende Nachricht speichern ---
        db_message = Message(conversation_id=conversation_id_value, content=masked_message)
        db.add(db_message)
        db.commit()
        db.refresh(db_message)

        # --- Chat Tracking ---
        if conversation_id not in CHATS:
            CHATS[conversation_id] = {
                "chat": model.start_chat(),
                "messages": [],
                "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
            }

        chat_data = CHATS[conversation_id]
        chat_data["messages"].append(("user", masked_message))

        # --- Model-Aufruf ---
        full_response = ""
        final_response = None
        for chunk in chat_data["chat"].send_message(masked_message, stream=True):
            if chunk.text:
                full_response += chunk.text
                final_response = chunk

        restored_response = restore_placeholders(full_response, mapping)

        # --- Antwort speichern ---
        db_resp_message = Message(conversation_id=conversation_id_value, content=restored_response)
        db.add(db_resp_message)
        db.commit()
        db.refresh(db_resp_message)

        chat_data["messages"].append(("assistant", restored_response))

        # --- Token & Kosten ---
        if final_response and getattr(final_response, "usage_metadata", None):
            usage = final_response.usage_metadata
            input_tokens = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0
            cost = (
                input_tokens * PRICES["gemini-2.5-flash"]["input"]
                + output_tokens * PRICES["gemini-2.5-flash"]["output"]
            )
            chat_data["usage"]["input_tokens"] += input_tokens
            chat_data["usage"]["output_tokens"] += output_tokens
            chat_data["usage"]["cost"] += cost
        else:
            input_tokens = output_tokens = cost = 0

        # 👇 hier sichern wir alle Rückgabedaten bevor Session zugeht
        result = {
            "conversation_id": conversation_id_value,
            "bot_message": restored_response,
            "input_tokens": chat_data["usage"]["input_tokens"],
            "output_tokens": chat_data["usage"]["output_tokens"],
            "cost_usd": round(chat_data["usage"]["cost"], 6)
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return result

