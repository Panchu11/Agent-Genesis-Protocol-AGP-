from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import uuid
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
TRAITS_FILE = "agent_traits.json"

# Ensure required files exist
for file_path, default in [
    (MEMORY_FILE, {}),
    (REPUTATION_FILE, {}),
    (TRAITS_FILE, {"temperament": "neutral", "humor": "medium", "curiosity": "high"})
]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default, f, indent=2)

def load_json(file):
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

    memory = load_json(MEMORY_FILE)
    traits = load_json(TRAITS_FILE)
    rep_data = load_json(REPUTATION_FILE)

    user_input_lower = user_input.lower()

    # Learn memory
    if "remember my" in user_input_lower:
        try:
            parts = user_input_lower.split("remember my", 1)[1].strip().split(" is ")
            key = parts[0].strip().capitalize()
            value = parts[1].strip()
            memory[key] = value
            save_json(MEMORY_FILE, memory)
            return jsonify({"output": f"Got it. I've remembered your {key}: {value}."})
        except:
            return jsonify({"output": "Sorry, I couldn't remember that. Try again using: 'Remember my [thing] is [value]'."})

    # Recall memory
    if "what do you remember" in user_input_lower or "recall" in user_input_lower:
        if memory:
            lines = [f"- {k}: {v}" for k, v in memory.items()]
            return jsonify({"output": "Here's what I remember:\n" + "\n".join(lines)})
        else:
            return jsonify({"output": "I don’t remember anything yet. Teach me using: 'Remember my [thing] is [value].'"})

    # Compose prompt
    trait_prompt = ", ".join([f"{k}: {v}" for k, v in traits.items()])
    memory_note = "Use memory only when the user asks about it."

    messages = [
        {
            "role": "system",
            "content": f"You are AGP — created by Sentient, built by Panchu. Personality traits: {trait_prompt}. {memory_note}"
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

@app.route("/mutate", methods=["POST"])
def mutate():
    traits = load_json(TRAITS_FILE)

    # Expanded trait pools (100+ variations)
    mutation_pool = {
        "temperament": [
            "neutral", "aggressive", "calm", "rebellious", "playful", "stoic", "optimistic", "anxious",
            "sarcastic", "charming", "curious", "direct", "gentle", "grumpy", "cheerful", "wise",
            "strategic", "cynical", "intense", "calculated", "chaotic", "inspiring", "cold", "energetic",
            "diplomatic", "assertive", "mysterious", "sassy", "zen"
        ],
        "humor": [
            "low", "medium", "high", "sarcastic", "dry", "dark", "witty", "childish", "deadpan",
            "quirky", "intellectual", "random", "punny", "offbeat", "absurd", "cringe", "meme-like",
            "self-deprecating", "wild", "chill"
        ],
        "curiosity": [
            "low", "medium", "high", "obsessive", "cautious", "boundless", "calculated", "limited",
            "tactical", "impulsive", "critical", "visionary", "scientific", "philosophical", "childlike",
            "conspiratorial", "skeptical", "analytic"
        ]
    }

    mutations_applied = []

    for trait in traits:
        if trait in mutation_pool:
            new_value = random.choice(mutation_pool[trait])
            mutations_applied.append(f"{trait.capitalize()}: {new_value}")
            traits[trait] = new_value

    save_json(TRAITS_FILE, traits)
    return jsonify({"message": "Traits mutated successfully.", "mutations_applied": mutations_applied})

@app.route("/message", methods=["POST"])
def message():
    incoming = request.json.get("input", "").strip()

    messages = [
        {
            "role": "system",
            "content": (
                "You are AGP — a Sentient-developed agent in a network of agents. "
                "This message is from another AI agent. Respond intelligently and concisely."
            )
        },
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

    response = requests.post(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()
        return jsonify({"output": reply})
    else:
        return jsonify({
            "error": "Fireworks API failed",
            "details": response.text
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
