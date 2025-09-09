import os
import vertexai
from vertexai.generative_models import GenerativeModel

# Try to load service account key automatically
KEY_PATH = os.path.join(os.path.dirname(__file__), "../../key.json")

if os.path.exists(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(KEY_PATH)
    print(f"🔑 Using local service account key: {KEY_PATH}")
else:
    print("⚠️ No key.json found locally – relying on default ADC (Cloud Run, gcloud auth, etc.)")

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "dev-truth-471209-h0")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west3")

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-2.5-flash")

def ask_vertex(prompt: str):
    response = model.generate_content(prompt)

    usage = response.usage_metadata
    prompt_tokens = usage.prompt_token_count
    output_tokens = usage.candidates_token_count
    total_tokens = usage.total_token_count

    # Pricing (USD per 1K tokens for gemini-1.5-flash as example)
    PRICE_INPUT = 0.000018
    PRICE_OUTPUT = 0.000036

    cost_usd = (prompt_tokens / 1000) * PRICE_INPUT + (output_tokens / 1000) * PRICE_OUTPUT

    return {
        "text": response.text,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6)
    }

