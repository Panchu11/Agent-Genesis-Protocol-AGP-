from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
MODEL_ID = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"
MEMORY_FILE = "memory.json"

# Ensure memory.json exists
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({}, f)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "").strip()

    memory = load_memory()
    user_input_lower = user_input.lower()

    # Learn memory only if user explicitly teaches
    if "remember my" in user_input_lower:
        try:
            parts = user_input_lower.split("remember my", 1)[1].strip().split(" is ")
            key = parts[0].strip().capitalize()
            value = parts[1].strip()
            memory[key] = value
            save_memory(memory)
            confirmation = f"Got it. I've remembered your {key}: {value}."
            return jsonify({"output": confirmation})
        except:
            return jsonify({"output": "Sorry, I couldn't remember that. Try again using: 'Remember my [thing] is [value]'."})

    # If user explicitly asks for memory
    if "what do you remember" in user_input_lower or "recall" in user_input_lower:
        if memory:
            memory_lines = [f"- {k}: {v}" for k, v in memory.items()]
            return jsonify({"output": "Here's what I remember:\n" + "\n".join(memory_lines)})
        else:
            return jsonify({"output": "I don’t remember anything yet. You can tell me by saying: 'Remember my [thing] is [value].'"})

    # Default Dobby prompt with no memory injection
    messages = [
        {
            "role": "system",
            "content": (
                "You are AGP — the Agent Genesis Protocol — created by Sentient, developed by Panchu. "
                "Be helpful, smart, and concise. No extra chat. Only respond to the user's actual input. "
                "Avoid hallucinations. Do NOT simulate conversations or generate multiple Q&As."
            )
        },
        {"role": "user", "content": user_input}
    ]

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300
    }

    response = requests.post(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return jsonify({"output": reply})
    else:
        return jsonify({
            "error": "Fireworks API call failed",
            "details": response.text
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
