from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "AGP is Live 🚀"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("input", "")
    if not user_input:
        return jsonify({"error": "Missing input"}), 400

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        "messages": [{"role": "user", "content": user_input}],
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
        return jsonify({"output": reply})
    else:
        return jsonify({
            "error": "Fireworks API call failed",
            "details": response.text
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
