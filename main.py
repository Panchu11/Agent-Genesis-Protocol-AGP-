from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
MEMORY_FILE = "memory.json"

# Load memory if exists
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
def home():
    return "AGP is Live with Memory 🧠"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "")
    if not user_input:
        return jsonify({"error": "Missing input"}), 400

    memory = load_memory()
    memory_context = "\n".join([f"{k}: {v}" for k, v in memory.items()])

    # Prompt with memory
    prompt = f"""
The user and you have the following memory context:
{memory_context}

User: {user_input}
AGP:
"""

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"]

        # Memory writing logic (basic version)
        if "remember" in user_input.lower() and " is " in user_input:
            parts = user_input.split(" is ")
            if len(parts) == 2:
                key = parts[0].replace("remember", "").strip().lower()
                value = parts[1].strip()
                memory[key] = value
                save_memory(memory)

        return jsonify({"output": reply})
    else:
        return jsonify({
            "error": "Fireworks API call failed",
            "details": response.text
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
