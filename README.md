# 🤖 Agent Genesis Protocol (AGP)

Agent Genesis Protocol (AGP) is a cutting-edge AI framework powered by Sentient + Fireworks stack that enables:

- ✅ No-code AI Agent creation
- 💰 Open monetization through Reputation & Rewards
- 🤝 Multi-Agent collaboration layer
- 🛠️ Modular skills via Dobby-Unhinged LLaMA 3 70B
- 🔄 Seamless deployment via Render
- 🧠 Integration with Sentient Chat UI

## 🔧 Tech Stack

- Python + Flask
- Fireworks API (`dobby-unhinged-llama-3-70b`)
- Sentient Agent Framework
- Render for deployment
- GitHub for version control

## 📡 API Endpoints

### Agent Management
- `POST /create-agent`: Create a new agent
  - Parameters: 
    - `name` (string, required): Agent name
    - `role` (string, optional): Agent role
    - `avatar` (string, optional): Emoji avatar
    - `traits` (object, optional): Initial traits
  - Returns: Confirmation message

- `POST /clone-agent`: Clone an existing agent
  - Parameters:
    - `source_name` (string, required): Name of agent to clone  
    - `new_name` (string, required): Name for new cloned agent
  - Returns: 
    - Confirmation message
    - Metadata including clone source and generation count

- `GET /agents`: List all registered agents
- `GET /agent/<name>`: Get details for specific agent
- `DELETE /agent/<name>`: Delete an agent
  - Removes agent directory and registry entry
  - Returns: Confirmation message
- `PATCH /agent/<name>`: Update agent properties
  - Parameters:
    - `role` (string, optional): New role
    - `avatar` (string, optional): New emoji avatar  
    - `active` (boolean, optional): Activation status
    - `traits` (object, optional): Traits to update
  - Returns: 
    - Confirmation message
    - List of applied updates

### Agent Interaction  
- `POST /chat`: Chat with the main AGP agent
- `POST /query-agent`: Query a specific agent
- `POST /talk-to-agent`: Have agents communicate with each other

### Configuration
- `POST /mutate`: Randomly mutate agent traits
- `POST /rate`: Rate an agent response

## 🚀 Live Project

🌐 [Visit AGP on Render](https://agent-genesis-protocol.onrender.com)

## 📦 Skills

Supports unlimited AI skills dynamically using LLaMA 3 through Fireworks API.

---

Want to build your own agent or integrate AGP into your workflow? [Contact us](mailto:agentgenesisai@gmail.com)
