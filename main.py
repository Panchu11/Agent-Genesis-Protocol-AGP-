from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import uuid
from datetime import datetime
import random
import sqlite3

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
MODEL_ID = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"

REPUTATION_FILE = "reputation.json"
TRAITS_FILE = "agent_traits.json"
DB_FILE = "agp_memory.db"
AGENTS_DIR = "agents"
REGISTRY_FILE = os.path.join(AGENTS_DIR, "registry.json")

os.makedirs(AGENTS_DIR, exist_ok=True)
for file_path, default in [
    (REPUTATION_FILE, {}),
    (TRAITS_FILE, {"temperament": "neutral", "humor": "medium", "curiosity": "high"}),
    (REGISTRY_FILE, {})
]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default, f, indent=2)

# Ensure SQLite table
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT,
    memory TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
conn.close()

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "").strip()

    traits = load_json(TRAITS_FILE)
    rep_data = load_json(REPUTATION_FILE)

    user_input_lower = user_input.lower()

    if "remember my" in user_input_lower:
        try:
            parts = user_input_lower.split("remember my", 1)[1].strip().split(" is ")
            key = parts[0].strip()
            value = parts[1].strip()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO memories (user_input, memory) VALUES (?, ?)", (key, value))
            conn.commit()
            conn.close()
            return jsonify({"output": f"Got it. I've remembered your {key}: {value}."})
        except:
            return jsonify({"output": "Sorry, I couldn't remember that. Use: 'Remember my [thing] is [value].'"})

    if "what do you remember" in user_input_lower or "recall" in user_input_lower:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_input, memory FROM memories")
        rows = c.fetchall()
        conn.close()
        if rows:
            lines = [f"- {k.strip().capitalize()}: {v}" for k, v in rows]
            return jsonify({"output": "Here's what I remember:\n" + "\n".join(lines)})
        else:
            return jsonify({"output": "I don’t remember anything yet. Teach me using: 'Remember my [thing] is [value].'"})

    trait_prompt = ", ".join([f"{k}: {v}" for k, v in traits.items()])
    system_msg = (
        f"You are AGP — created by Sentient, built by Panchu. "
        f"Traits: {trait_prompt}. Use memory only when the user asks."
    )

    messages = [
        {"role": "system", "content": system_msg},
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
        msg_id = str(uuid.uuid4())
        rep_data[msg_id] = {
            "timestamp": str(datetime.utcnow()),
            "prompt": user_input,
            "response": reply,
            "score": 0
        }
        save_json(REPUTATION_FILE, rep_data)
        return jsonify({"output": reply})
    else:
        return jsonify({
            "error": "Fireworks API call failed",
            "details": response.text
        }), 500

@app.route("/mutate", methods=["POST"])
def mutate():
    traits = load_json(TRAITS_FILE)
    mutation_pool = {
        "temperament": ["neutral", "aggressive", "calm", "rebellious", "playful", "stoic"],
        "humor": ["low", "medium", "high", "sarcastic", "dry", "dark"],
        "curiosity": ["low", "medium", "high", "obsessive", "cautious"],
        "empathy": ["low", "balanced", "high", "robotic"],
        "tone": ["professional", "casual", "chaotic", "sassy"],
        "intellect": ["basic", "advanced", "scholarly", "genius"],
        "logic": ["emotional", "logical", "analytical"],
        "sarcasm": ["none", "light", "frequent", "extreme"]
    }

    mutated = []
    for trait in traits:
        if trait in mutation_pool:
            new_val = random.choice(mutation_pool[trait])
            traits[trait] = new_val
            mutated.append(f"{trait}: {new_val}")

    save_json(TRAITS_FILE, traits)
    return jsonify({"message": "Traits mutated successfully.", "mutations_applied": mutated})

@app.route("/rate", methods=["POST"])
def rate():
    data = request.json
    rep_data = load_json(REPUTATION_FILE)
    msg_id = data.get("id")
    rating = data.get("score")

    if msg_id in rep_data:
        rep_data[msg_id]["score"] = rating
        save_json(REPUTATION_FILE, rep_data)
        return jsonify({"message": "Reputation updated successfully."})
    return jsonify({"error": "Message ID not found."}), 404

@app.route("/message", methods=["POST"])
def message():
    incoming = request.json.get("input", "").strip()

    messages = [
        {"role": "system", "content": (
            "You are AGP — a Sentient-developed agent in a network of agents. "
            "This message is from another AI agent. Respond intelligently and concisely."
        )},
        {"role": "user", "content": incoming}
    ]

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 250
    }

    response = requests.post("https://api.fireworks.ai/inference/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()
        return jsonify({"output": reply})
    else:
        return jsonify({"error": "Fireworks API failed", "details": response.text}), 500

# ✅ Agent Registry
@app.route("/register", methods=["POST"])
def register_agent():
    data = request.json
    name = data.get("name")
    role = data.get("role", "default")
    avatar = data.get("avatar", "🤖")
    active = data.get("active", True)

    registry = load_json(REGISTRY_FILE)
    registry[name] = {
        "role": role,
        "avatar": avatar,
        "active": active,
        "created": str(datetime.utcnow())
    }
    save_json(REGISTRY_FILE, registry)
    return jsonify({"message": f"Agent '{name}' registered."})

@app.route("/agents", methods=["GET"])
def list_agents():
    return jsonify(load_json(REGISTRY_FILE))

@app.route("/agent/<name>", methods=["GET"])
def get_agent(name):
    registry = load_json(REGISTRY_FILE)
    if name in registry:
        return jsonify(registry[name])
    else:
        return jsonify({"error": "Agent not found."}), 404

# ✅ Query Agent by name (new feature)
@app.route("/query-agent", methods=["POST"])
def query_agent():
    data = request.json
    agent_name = data.get("name")
    question = data.get("input")

    if not agent_name or not question:
        return jsonify({"error": "Missing name or input."}), 400

    registry = load_json(REGISTRY_FILE)
    if agent_name not in registry:
        return jsonify({"error": f"Agent '{agent_name}' not found."}), 404

    traits_path = os.path.join(AGENTS_DIR, agent_name, "traits.json")
    if not os.path.exists(traits_path):
        return jsonify({"error": f"No traits found for '{agent_name}'."}), 404

    traits = load_json(traits_path)
    trait_desc = ", ".join([f"{k}: {v}" for k, v in traits.items()])
    prompt = (
        f"You are {agent_name}, a clone of AGP with these traits: {trait_desc}. "
        f"Respond to the user query clearly.\n\n"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question}
    ]

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 250
    }

    response = requests.post("https://api.fireworks.ai/inference/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()
        return jsonify({"output": reply})
    else:
        return jsonify({"error": "Fireworks API failed", "details": response.text}), 500

if __name__ == "__main__":
    app.run(debug=True)
