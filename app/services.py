import os
from google.oauth2 import service_account
from google.cloud import secretmanager
import vertexai
from vertexai.generative_models import GenerativeModel


def _access_secret(secret_path: str) -> str:
    """Load secret either from env (Cloud Run) or directly from Secret Manager (local)."""
    # Case 1: Cloud Run setzt env-Variable direkt (z.B. --set-secrets)
    if os.path.exists(secret_path):
        # Falls es ein gemountetes File ist (Cloud Run secret volumes)
        with open(secret_path, "r") as f:
            return f.read()
    if secret_path in os.environ:
        return os.environ[secret_path]

    # Case 2: Lokal via Secret Manager API
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_path)
    return response.payload.data.decode("UTF-8")


# --- Initialisierung VertexAI ---
def _init_vertexai():
    json_key = _access_secret(
        "projects/1094405818622/secrets/officeai-sa-key/versions/1"
    )

    # Service Account Key temporär schreiben (braucht Dateipfad für google-auth)
    key_path = "/tmp/sa.json"
    with open(key_path, "w") as f:
        f.write(json_key)

    creds = service_account.Credentials.from_service_account_file(key_path)

    vertexai.init(
        project=os.environ.get("GCP_PROJECT", "dev-truth-471209-h0"),
        location="us-central1",  # anpassen falls nötig
        credentials=creds,
    )


_init_vertexai()


def call_vertex(message: str) -> str:
    model = GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(message)
    return response.text


def get_pat_token() -> str:
    return _access_secret(
        "projects/1094405818622/secrets/github_rmeier_pat_token/versions/1"
    )
