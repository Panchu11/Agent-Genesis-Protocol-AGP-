from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import uuid
import requests
from datetime import datetime
import random

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
MODEL_ID = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"
MEMORY_FILE = "memory.json"
REPUTATION_FILE = "reputation.json"
TRAITS_FILE = "traits.json"

# Ensure JSON files exist
for file in [MEMORY_FILE, REPUTATION_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "").strip()
    memory = load_json(MEMORY_FILE)
    user_input_lower = user_input.lower()

    # Memory input
    if "remember my" in user_input_lower:
        try:
            parts = user_input_lower.split("remember my", 1)[1].strip().split(" is ")
            key = parts[0].strip().capitalize()
            value = parts[1].strip()
            memory[key] = value
            save_json(MEMORY_FILE, memory)
            return jsonify({"output": f"Got it. I've remembered your {key}: {value}."})
        except:
            return jsonify({"output": "Couldn't process that. Use 'Remember my [thing] is [value]'."})

    # Recall memory
    if "what do you remember" in user_input_lower or "recall" in user_input_lower:
        if memory:
            lines = [f"- {k}: {v}" for k, v in memory.items()]
            return jsonify({"output": "Here's what I remember:\n" + "\n".join(lines)})
        return jsonify({"output": "I don’t remember anything yet. Tell me something to remember!"})

    # AGP system prompt
    messages = [
        {
            "role": "system",
            "content": (
                "You are AGP — the Agent Genesis Protocol — created by Sentient, developed by Panchu. "
                "Be helpful, smart, and concise. Do NOT simulate conversation. Respond only to the current prompt."
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

    response = requests.post("https://api.fireworks.ai/inference/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()

        # Reputation log
        rep_data = load_json(REPUTATION_FILE)
        rep_id = str(uuid.uuid4())
        rep_data[rep_id] = {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": user_input,
            "response": reply,
            "score": 0
        }
        save_json(REPUTATION_FILE, rep_data)

        return jsonify({"output": reply, "id": rep_id})
    else:
        return jsonify({
            "error": "Fireworks API call failed",
            "details": response.text
        }), 500

@app.route("/rate", methods=["POST"])
def rate():
    data = request.json
    rep_id = data.get("id")
    score = data.get("score")
    rep_data = load_json(REPUTATION_FILE)

    if rep_id in rep_data:
        rep_data[rep_id]["score"] = score
        save_json(REPUTATION_FILE, rep_data)
        return jsonify({"message": "Rating recorded"})
    return jsonify({"error": "ID not found"}), 404

@app.route("/mutate", methods=["POST"])
def mutate():
    traits = load_json(TRAITS_FILE)
    base = traits.get("base_traits", [])
    mutations = traits.get("mutations", [])

    # Select up to 3 random mutations
    selected = random.sample(mutations, 3)
    mutated_prompt = base + selected

    return jsonify({
        "system_prompt": "\n".join(mutated_prompt),
        "mutations_applied": selected
    })

if __name__ == "__main__":
    app.run(debug=True)
