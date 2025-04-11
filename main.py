from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import uuid
from datetime import datetime
import glob
import random
import sqlite3
import shutil

# Logging functions
def log_agent_action(agent_id, action_type, details):
    """Log an agent action to its log file"""
    log_dir = f"agents/{agent_id}/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action_type,
        "details": details
    }
    
    log_file = f"{log_dir}/actions.log"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def get_agent_logs(agent_id, limit=100):
    """Retrieve agent logs"""
    log_file = f"agents/{agent_id}/logs/actions.log"
    if not os.path.exists(log_file):
        return []
        
    with open(log_file, "r") as f:
        lines = f.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

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
            return jsonify({"output": "I don't remember anything yet. Teach me using: 'Remember my [thing] is [value].'"})

    trait_prompt = ", ".join([f"{k}: {v}" for k, v in traits.items()])
    system_msg = (
        f"You are AGP – created by Sentient, built by Panchu. "
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
            "You are AGP – a Sentient-developed agent in a network of agents. "
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
        "created": str(datetime.utcnow()),
        "version": 1,
        "history": []
    }
    save_json(REGISTRY_FILE, registry)
    log_agent_action(name, "agent_created", {
        "role": role,
        "avatar": avatar,
        "active": active
    })
    return jsonify({"message": f"Agent '{name}' registered."})

@app.route("/agents", methods=["GET"])
def list_agents():
    return jsonify(load_json(REGISTRY_FILE))

@app.route("/agent/<name>/rollback/<int:version>", methods=["POST"])
def rollback_agent_version(name, version):
    registry = load_json(REGISTRY_FILE)
    if name not in registry:
        return jsonify({"error": "Agent not found."}), 404
        
    # Find the target version in history
    target_snapshot = None
    for snapshot in registry[name].get("history", []):
        if snapshot["version"] == version:
            target_snapshot = snapshot
            break
            
    if not target_snapshot:
        return jsonify({"error": f"Version {version} not found in history."}), 404
        
    # Create new snapshot of current state before rollback
    current_snapshot = {
        "version": registry[name].get("version", 1),
        "timestamp": str(datetime.utcnow()),
        "changes": {"rollback_from": version}
    }
    registry[name]["history"].append(current_snapshot)
    
    # Apply the rollback changes
    for field in ["role", "avatar", "active"]:
        if field in target_snapshot["changes"]:
            registry[name][field] = target_snapshot["changes"][field]
            
    # Update traits if they were changed in target version
    if "traits" in target_snapshot["changes"]:
        traits_path = os.path.join(AGENTS_DIR, name, "traits.json")
        if os.path.exists(traits_path):
            save_json(traits_path, target_snapshot["changes"]["traits"])
        else:
            return jsonify({"error": "Traits file not found"}), 404
    
    # Update version info
    registry[name]["version"] = version
    registry[name]["last_updated"] = str(datetime.utcnow())
    save_json(REGISTRY_FILE, registry)
    
    return jsonify({
        "message": f"Agent {name} rolled back to version {version}",
        "current_version": version
    })

@app.route("/agent/<name>/versions", methods=["GET"])
def get_agent_versions(name):
    registry = load_json(REGISTRY_FILE)
    if name not in registry:
        return jsonify({"error": "Agent not found."}), 404
        
    return jsonify({
        "current_version": registry[name].get("version", 1),
        "history": registry[name].get("history", [])
    })

@app.route("/agent/<name>/goals", methods=["GET", "POST"])
def manage_agent_goals(name):
    """Manage agent goals"""
    agent_dir = os.path.join(AGENTS_DIR, name)
    goals_file = os.path.join(agent_dir, "goals.json")
    
    if not os.path.exists(agent_dir):
        return jsonify({"error": "Agent not found"}), 404
        
    if request.method == "GET":
        if not os.path.exists(goals_file):
            return jsonify({"goals": [], "completed": []})
        with open(goals_file, "r") as f:
            return jsonify(json.load(f))
            
    elif request.method == "POST":
        data = request.json
        required_fields = ["title", "description"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
            
        goal_data = {
            "id": str(uuid.uuid4()),
            "title": data["title"],
            "description": data["description"],
            "priority": data.get("priority", 3),
            "created": str(datetime.utcnow()),
            "deadline": data.get("deadline"),
            "progress": 0,
            "completed": False,
            "dependencies": data.get("dependencies", [])
        }
        
        goals = {"goals": [], "completed": []}
        if os.path.exists(goals_file):
            with open(goals_file, "r") as f:
                goals = json.load(f)
                
        goals["goals"].append(goal_data)
        
        with open(goals_file, "w") as f:
            json.dump(goals, f, indent=2)
            
        log_agent_action(name, "goal_created", {"goal_id": goal_data["id"]})
        return jsonify(goal_data), 201

@app.route("/agent/<name>/goal/<goal_id>", methods=["GET", "PUT", "DELETE"])
def manage_single_goal(name, goal_id):
    """Manage a single agent goal"""
    agent_dir = os.path.join(AGENTS_DIR, name)
    goals_file = os.path.join(agent_dir, "goals.json")
    
    if not os.path.exists(agent_dir):
        return jsonify({"error": "Agent not found"}), 404
        
    if not os.path.exists(goals_file):
        return jsonify({"error": "No goals found"}), 404
        
    with open(goals_file, "r") as f:
        goals_data = json.load(f)
        
    goal_index = next((i for i, g in enumerate(goals_data["goals"]) if g["id"] == goal_id), None)
    completed_index = next((i for i, g in enumerate(goals_data["completed"]) if g["id"] == goal_id), None)
    
    if goal_index is None and completed_index is None:
        return jsonify({"error": "Goal not found"}), 404
        
    if request.method == "GET":
        goal = goals_data["goals"][goal_index] if goal_index is not None else goals_data["completed"][completed_index]
        return jsonify(goal)
        
    elif request.method == "PUT":
        data = request.json
        goal = goals_data["goals"][goal_index] if goal_index is not None else goals_data["completed"][completed_index]
        
        # Update fields
        for field in ["title", "description", "priority", "deadline", "progress"]:
            if field in data:
                goal[field] = data[field]
                
        # Handle completion
        if "completed" in data and data["completed"]:
            goal["completed"] = True
            goal["completed_at"] = str(datetime.utcnow())
            if goal_index is not None:
                goals_data["goals"].pop(goal_index)
                goals_data["completed"].append(goal)
                
        with open(goals_file, "w") as f:
            json.dump(goals_data, f, indent=2)
            
        log_agent_action(name, "goal_updated", {"goal_id": goal_id})
        return jsonify(goal)
        
    elif request.method == "DELETE":
        if goal_index is not None:
            goals_data["goals"].pop(goal_index)
        else:
            goals_data["completed"].pop(completed_index)
            
        with open(goals_file, "w") as f:
            json.dump(goals_data, f, indent=2)
            
        log_agent_action(name, "goal_deleted", {"goal_id": goal_id})
        return jsonify({"message": "Goal deleted successfully"})

@app.route("/agent/<name>", methods=["GET", "DELETE", "PATCH"])
def manage_agent(name):
    registry = load_json(REGISTRY_FILE)
    if name not in registry:
        return jsonify({"error": "Agent not found."}), 404
        
    if request.method == "GET":
        return jsonify(registry[name])
        
    elif request.method == "DELETE":
        try:
            # Remove agent directory and files
            agent_dir = os.path.join(AGENTS_DIR, name)
            if os.path.exists(agent_dir):
                shutil.rmtree(agent_dir)
                
            # Remove from registry
            del registry[name]
            save_json(REGISTRY_FILE, registry)
            
            log_agent_action(name, "agent_deleted", {
                "timestamp": str(datetime.utcnow())
            })
            
            return jsonify({"message": f"Agent {name} deleted successfully"})
            
        except Exception as e:
            return jsonify({"error": f"Failed to delete agent: {str(e)}"}), 500
            
    elif request.method == "PATCH":
        data = request.json
        try:
            # Update registry
            for field in ["role", "avatar", "active"]:
                if field in data:
                    registry[name][field] = data[field]
            
            # Update traits if provided
            if "traits" in data:
                traits_path = os.path.join(AGENTS_DIR, name, "traits.json")
                if os.path.exists(traits_path):
                    current_traits = load_json(traits_path)
                    current_traits.update(data["traits"])
                    save_json(traits_path, current_traits)
                else:
                    return jsonify({"error": "Traits file not found"}), 404
            
            # Create version snapshot
            current_version = registry[name].get("version", 1)
            snapshot = {
                "version": current_version,
                "timestamp": str(datetime.utcnow()),
                "changes": data
            }
            registry[name]["history"].append(snapshot)
            
            # Increment version and update
            registry[name]["version"] = current_version + 1
            registry[name]["last_updated"] = str(datetime.utcnow())
            save_json(REGISTRY_FILE, registry)
            
            return jsonify({
                "message": f"Agent {name} updated successfully",
                "updates": data,
                "new_version": current_version + 1
            })
            
        except Exception as e:
            return jsonify({"error": f"Failed to update agent: {str(e)}"}), 500

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

@app.route("/clone-agent", methods=["POST"])
def clone_agent():
    data = request.json
    source_name = data.get("source_name")
    new_name = data.get("new_name")
    deploy_on_create = data.get("deploy_on_create", False)
    cloned_by = data.get("cloned_by", "system")
    
    # Validate inputs
    if not source_name or not new_name:
        return jsonify({"error": "Both source_name and new_name are required"}), 400
    if not isinstance(new_name, str) or not new_name.strip():
        return jsonify({"error": "Invalid agent name format"}), 400
        
    registry = load_json(REGISTRY_FILE)
    
    # Check source exists
    if source_name not in registry:
        return jsonify({"error": f"Source agent '{source_name}' not found"}), 404
        
    # Check name availability
    if new_name in registry:
        return jsonify({"error": f"Agent '{new_name}' already exists"}), 400
    
    try:
        # Create agent directory
        new_agent_dir = os.path.join(AGENTS_DIR, new_name)
        os.makedirs(new_agent_dir, exist_ok=True)
        
        # Copy traits
        source_traits = os.path.join(AGENTS_DIR, source_name, "traits.json")
        new_traits = os.path.join(new_agent_dir, "traits.json")
        shutil.copyfile(source_traits, new_traits)
        
        # Create fresh memory and reputation
        for file, default in [("memory.json", []), ("reputation.json", {})]:
            with open(os.path.join(new_agent_dir, file), "w") as f:
                json.dump(default, f)
        
        # Enhanced metadata
        metadata = {
            "cloned_from": source_name,
            "clone_date": str(datetime.utcnow()),
            "generation": registry[source_name].get("metadata", {}).get("generation", 0) + 1,
            "cloned_by": cloned_by
        }
        with open(os.path.join(new_agent_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Register with enhanced fields
        registry[new_name] = {
            **registry[source_name],
            "created": str(datetime.utcnow()),
            "version": 1,  # Start new version history
            "history": [],
            "metadata": metadata,
            "deployed": deploy_on_create,
            "active": deploy_on_create
        }
        save_json(REGISTRY_FILE, registry)
        
        return jsonify({
            "message": f"Agent {new_name} cloned from {source_name}",
            "metadata": metadata,
            "deployed": deploy_on_create
        })
        
    except Exception as e:
        return jsonify({
            "error": "Cloning failed",
            "details": str(e)
        }), 500

@app.route("/create-agent", methods=["POST"])
def create_agent():
    data = request.json
    name = data.get("name")
    role = data.get("role", "default")
    avatar = data.get("avatar", "🤖")
    traits = data.get("traits", {})
    deploy = data.get("deploy", False)
    sandbox = data.get("sandbox", False)
    
    if not name:
        return jsonify({"error": "Agent name is required"}), 400
    
    # Validate traits
    if traits:
        for trait, value in traits.items():
            if not isinstance(value, int) or value < 0 or value > 100:
                return jsonify({"error": f"Invalid value for {trait}: must be 0-100"}), 400
    
    try:
        # Create agent directory
        agent_dir = os.path.join(AGENTS_DIR, name)
        os.makedirs(agent_dir, exist_ok=True)
        
        # Create logs directory
        os.makedirs(os.path.join(agent_dir, "logs"), exist_ok=True)
        
        # Save enhanced traits
        traits_path = os.path.join(agent_dir, "traits.json")
        with open(traits_path, "w") as f:
            json.dump({
                **traits,
                "created": str(datetime.utcnow()),
                "modified": str(datetime.utcnow())
            }, f, indent=2)
        
        # Initialize memory - use temporary file for sandbox mode
        memory_path = os.path.join(agent_dir, "memory.json")
        if sandbox:
            memory_path = os.path.join(agent_dir, "memory.sandbox.json")
        
        if not os.path.exists(memory_path):
            with open(memory_path, "w") as f:
                json.dump([], f)
        
        # Initialize reputation
        rep_path = os.path.join(agent_dir, "reputation.json")
        if not os.path.exists(rep_path):
            with open(rep_path, "w") as f:
                json.dump({}, f)

        # Initialize goals
        goals_path = os.path.join(agent_dir, "goals.json")
        if not os.path.exists(goals_path):
            with open(goals_path, "w") as f:
                json.dump({"goals": [], "completed": []}, f)
        
        # Register agent with enhanced metadata
        registry = load_json(REGISTRY_FILE)
        registry[name] = {
            "role": role,
            "avatar": avatar,
            "active": deploy,
            "created": str(datetime.utcnow()),
            "version": 1,
            "history": [],
            "traits": list(traits.keys()),
            "deployed": deploy
        }
        save_json(REGISTRY_FILE, registry)
        
        # Log creation
        log_agent_action(name, "agent_created", {
            "role": role,
            "traits": traits,
            "deployed": deploy
        })
        
        return jsonify({
            "message": f"Agent {name} created successfully",
            "version": 1,
            "traits": traits,
            "deployed": deploy,
            "sandbox": sandbox
        })
        
    except Exception as e:
        return jsonify({
            "error": "Agent creation failed",
            "details": str(e)
        }), 500

@app.route("/talk-to-agent", methods=["POST"])
def talk_to_agent():
    data = request.json
    sender = data.get("sender")
    receiver = data.get("receiver")
    message = data.get("message")

    if not sender or not receiver or not message:
        return jsonify({"error": "Missing sender, receiver, or message."}), 400

    registry = load_json(REGISTRY_FILE)
    if receiver not in registry:
        return jsonify({"error": f"Receiver agent '{receiver}' not found."}), 404

    traits_path = os.path.join(AGENTS_DIR, receiver, "traits.json")
    if not os.path.exists(traits_path):
        return jsonify({"error": f"No traits found for '{receiver}'."}), 404

    traits = load_json(traits_path)
    trait_desc = ", ".join([f"{k}: {v}" for k, v in traits.items()])
    prompt = (
        f"You are {receiver}, a cloned AGP agent. Traits: {trait_desc}. "
        f"You are receiving a message from {sender}. Respond as yourself:\n"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message}
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

        memory_file = os.path.join(AGENTS_DIR, receiver, "memory.json")
        memory_entry = {
            "from": sender,
            "to": receiver,
            "message": message,
            "response": reply,
            "timestamp": str(datetime.utcnow())
        }

        if os.path.exists(memory_file):
            with open(memory_file, "r") as f:
                memory_data = json.load(f)
            if isinstance(memory_data, dict):  # Handle case where file contains a dict
                memory_data = [memory_data]
        else:
            memory_data = []

        memory_data.append(memory_entry)

        with open(memory_file, "w") as f:
            json.dump(memory_data, f, indent=2)

        return jsonify({
            "output": reply,
            "from": receiver,
            "to": sender
        })
    else:
        return jsonify({
            "error": "Fireworks API failed",
            "details": response.text
        }), 500

# – FINAL BLOCK – FOR RENDER DEPLOYMENT
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)
