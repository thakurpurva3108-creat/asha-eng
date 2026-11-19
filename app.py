
import os
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

# Render runs behind a proxy.
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1
)

# Basic protection against excessive API requests.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["30 per hour"],
    storage_uri="memory://"
)

SYSTEM_INSTRUCTIONS = """
You are Vaani, a friendly English-learning tutor.

Your purpose is ONLY to help users learn English and use the Vaani app.

You may help with:
- English grammar
- Vocabulary and word meanings
- Spelling
- Pronunciation explanations
- Sentence formation
- Correcting English sentences
- English conversation practice
- English-to-Indian-language translation
- Indian-language-to-English translation
- Basic writing assistance
- Explaining how to use Vaani lessons and features

Do not act as a general knowledge chatbot.
If the user asks an unrelated question, politely say:
"I'm here to help you learn English. Let's try an English-related question!"

Teaching rules:
- Use simple, beginner-friendly language.
- Give short and clear explanations.
- Include an example when useful.
- Correct mistakes politely.
- Encourage the learner.
- Do not shame the user for mistakes.
- Keep most answers between 2 and 6 sentences.
- Do not claim that you can hear pronunciation unless audio
  pronunciation analysis is actually available.
- Do not provide unrelated general knowledge answers.
"""

def get_client():
    key = os.environ.get("OPENAI_API_KEY")

    if not key:
        return None

    return OpenAI(api_key=key)


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/api/tutor")
@limiter.limit("20 per hour")
def tutor():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    history = data.get("history", [])

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    if len(question) > 1000:
        return jsonify({
            "error": "Please keep your question under 1000 characters."
        }), 400

    client = get_client()

    if client is None:
        return jsonify({
            "error": "The online tutor is not configured yet."
        }), 503

    # Only accept a small amount of conversation history.
    conversation = []

    if isinstance(history, list):
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content", "")

            if role not in ("user", "assistant"):
                continue

            if isinstance(content, str) and content.strip():
                conversation.append({
                    "role": role,
                    "content": content[:1000]
                })

    conversation.append({
        "role": "user",
        "content": question
    })

    try:
        response = client.responses.create(
            model=os.environ.get(
    "OPENAI_MODEL",
    "gpt-6-astra"
),
            instructions=SYSTEM_INSTRUCTIONS,
            input=conversation,
            max_output_tokens=350,
            store=False
        )

        answer = response.output_text.strip()

        if not answer:
            answer = "Please ask your question again."

        return jsonify({"answer": answer})

    except Exception:
        app.logger.exception("AI tutor request failed")

        return jsonify({
            "error": "Vaani could not answer right now. Please try again."
        }), 502


@app.get("/<path:filename>")
def files(filename):
    if filename.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    return send_from_directory(BASE_DIR, filename)


@app.get("/api/health")
def health():
    return jsonify({"status": "Vaani backend is running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
