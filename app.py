import json
import os

import cohere
from decouple import config
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template

load_dotenv()

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDS_PATH = os.path.join(BASE_DIR, "record.json")

COHERE_API_KEY = os.getenv("COHERE_API_KEY") or config("COHERE_API_KEY", default=None)
COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-english-v3.0")

if not COHERE_API_KEY:
    raise ValueError("Missing COHERE_API_KEY in environment")

cohere_client = cohere.Client(COHERE_API_KEY)

records = []


def load_records():
    with open(RECORDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_local_records():
    global records
    records = load_records()
    return records


def save_external_record(question, answer):
    """Append an externally-sourced Q/A to the persistent record file.

    Skips saving if the answer is the known fallback or if the question already
    exists in the records (case-insensitive match).
    """
    global records
    fallback = "I couldn't find a relevant answer."
    if not answer or not answer.strip() or answer.strip() == fallback:
        return
    try:
        current = load_records()
    except Exception:
        current = []

    q_norm = str(question).strip().lower()
    if any(str(r.get("question", "")).strip().lower() == q_norm for r in current):
        print("[save_external_record] Question already exists — not saving")
        return

    new_id = max((int(r.get("id", 0)) for r in current), default=0) + 1
    new_rec = {"id": new_id, "question": question, "answer": answer}
    current.append(new_rec)
    try:
        with open(RECORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        records = current
        print(f"[save_external_record] Saved new record id={new_id}")
    except Exception as e:
        print(f"[save_external_record] Failed to save record: {e}")

#cohore updated model find from here https://docs.cohere.com/docs/models#command
def fetch_remote_answer(user_input):
    """Query a remote provider for an answer when no local match is found.

    The implementation attempts several provider model names for compatibility
    with the installed client. Returns a string answer or the standard fallback
    message when nothing suitable is found.
    """
    models_to_try = ["command-r7b-12-2024", "command-a-plus-05-2026", "command-r-plus", "command", "command-light"]

    for model_name in models_to_try:
        try:
            response = cohere_client.chat(
                model=model_name,
                message=f"Answer the user's question clearly and concisely.\n\nUser: {user_input}",
            )

            # Collect textual content from common response shapes
            candidate_texts = []
            if hasattr(response, "text") and isinstance(response.text, str):
                candidate_texts.append(response.text)
            if hasattr(response, "message") and response.message is not None:
                message = response.message
                if hasattr(message, "content") and isinstance(message.content, list):
                    for item in message.content:
                        if hasattr(item, "text") and isinstance(item.text, str):
                            candidate_texts.append(item.text)
                        elif isinstance(item, str):
                            candidate_texts.append(item)
                elif isinstance(message, str):
                    candidate_texts.append(message)
            if hasattr(response, "content") and isinstance(response.content, list):
                for item in response.content:
                    if hasattr(item, "text") and isinstance(item.text, str):
                        candidate_texts.append(item.text)
                    elif isinstance(item, str):
                        candidate_texts.append(item)
            if isinstance(response, str):
                candidate_texts.append(response)

            for text in candidate_texts:
                cleaned = str(text).strip()
                if cleaned:
                    return cleaned

            if hasattr(response, "__dict__"):
                for value in response.__dict__.values():
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except Exception:
            # Try next model silently
            continue

    return "I couldn't find a relevant answer."


def retrieve_answer(user_input):
    if not records:
        load_local_records()

    if not records:
        return "No records are available for retrieval."

    user_input_lower = user_input.lower()
    matches = []

    for record in records:
        question = str(record.get("question", "")).lower()
        answer = str(record.get("answer", "")).lower()
        if user_input_lower in question or user_input_lower in answer:
            matches.append(record.get("answer", "No answer found."))

    if matches:
        formatted = []
        for index, match in enumerate(matches):
            if index == 0:
                formatted.append(f"<b>{match}</b>")
            else:
                formatted.append(match)
        return "<br>".join(formatted)

    # No local match — query external AI and persist the result for future use.
    ext_reply = answer_with_external_ai(user_input)
    if ext_reply and ext_reply.strip() and ext_reply.strip() != "I couldn't find a relevant answer.":
        save_external_record(user_input, ext_reply)
    return ext_reply


def ensure_records_loaded():
    global records
    current_records = load_records()
    if current_records != records:
        records = current_records


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Chat API is running. Use POST /chat."})


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Please provide a message."}), 400

    ensure_records_loaded()
    reply = retrieve_answer(user_input)
    if not isinstance(reply, str):
        reply = str(reply)
    return jsonify({"reply": reply})


@app.route("/ui", methods=["GET"])
def ui():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
