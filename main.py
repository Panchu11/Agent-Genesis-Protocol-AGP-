from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
MODEL_ID = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"
MEMORY_FILE = "memory.json"

# Ensure memory file exists
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
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "").strip()
    memory = load_memory()
    context = "\n".join([f"{k}: {v}" for k, v in memory.items()])

    prompt = f"""
You are AGP, a powerful assistant created through the Agent Genesis Protocol.

Known memory:
{context}

User: {user_input}
AGP:
    """

    payload = {
        "model": MODEL_ID,
        "prompt": prompt,
        "max_tokens": 300,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.fireworks.ai/inference/v1/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        output = response.json()["choices"][0]["text"].strip()

        # Check for memory storage intent
        if "remember my" in user_input.lower():
            try:
                parts = user_input.lower().split("remember my", 1)[1].strip().split(" is ")
                key = parts[0].strip()
                value = parts[1].strip()
                memory[key] = value
                save_memory(memory)
            except:
                pass

        return jsonify({"output": output})
    else:
        return jsonify({"error": "Fireworks API call failed", "details": response.text}), 500

if __name__ == "__main__":
    app.run(debug=True)
