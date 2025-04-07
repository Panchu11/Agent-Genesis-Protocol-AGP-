import os
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "fw_3ZXXr9SL3uJDwVZR6gpEPw8n")
MODEL_URL = "https://api.fireworks.ai/inference/v1/completions"

def generate_response(prompt):
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "accounts/fireworks/models/dobby-unhinged-llama-3-70b",
        "prompt": prompt,
        "max_tokens": 1000,
        "stream": False
    }
    response = requests.post(MODEL_URL, headers=headers, json=data)
    return response.json().get("choices", [{}])[0].get("text", "").strip()

@app.route("/agent", methods=["POST"])
def agent():
    user_input = request.json.get("input", "")
    if not user_input:
        return jsonify({"error": "Missing input"}), 400

    response = generate_response(user_input)
    return jsonify({"output": response})

@app.route("/")
def home():
    return "AGP Dobby Unhinged Agent is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
