# ODLA - Distributed Ollama Inference Network

A minimal distributed inference network that allows multiple nodes to expose local Ollama models through a central operator, enabling clients to run inference requests across the network with streamed responses.

## Architecture

```
client.py  →  server.py  →  node.py  →  Ollama API
```

### Components

| Component | Responsibility | Tech Stack |
|-----------|---------------|------------|
| **Operator** | Node registry, request routing, stream relay | FastAPI, asyncio, httpx |
| **Node Agent** | Auto-register with operator, execute jobs via local Ollama | FastAPI, Ollama Python SDK |
| **Client CLI** | Submit prompts, receive streamed responses | Typer, httpx |
| **Ollama Runtime** | Local model execution | Ollama HTTP API (localhost:11434) |

## Features

- **Automatic Node Discovery**: Nodes detect and register their available Ollama models on startup
- **Round-Robin Load Balancing**: Operator distributes requests across available nodes
- **Streaming Responses**: Real-time token streaming from models to client
- **Health Monitoring**: Automatic health checks and stale node pruning
- **JSON Line Protocol**: Structured streaming format for reliable parsing
- **Docker Support**: Easy deployment with Docker Compose

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running locally
- At least one Ollama model pulled (e.g., `ollama pull llama3`)

### Installation

1. **Clone and setup**
   ```bash
   cd /path/to/odla
   pip install -r requirements.txt
   ```

2. **Verify Ollama is running**
   ```bash
   ollama list
   ```

### Running Locally (Without Docker)

#### Terminal 1: Start Operator
```bash
python server.py
```

#### Terminal 2: Start Node Agent
```bash
python node.py
```

The node will automatically:
- Detect available Ollama models
- Register with the operator
- Start accepting inference jobs

#### Terminal 3: Run Client
```bash
# Basic inference
python client.py "Explain quantum entanglement in simple terms" --model llama3

# List registered nodes
python client.py nodes
```

### Running with Docker Compose

This setup runs 1 operator and 2 node agents, all connecting to Ollama on your host machine.

1. **Start Ollama on host** (if not already running)
   ```bash
   ollama serve
   ```

2. **Start the distributed network**
   ```bash
   docker-compose up --build
   ```

3. **Run client** (from host)
   ```bash
   python client.py "Write a haiku about distributed computing" --model llama3
   ```

4. **View registered nodes**
   ```bash
   python client.py nodes
   ```

## Configuration

Edit `config.json` to customize settings:

```json
{
  "operator_url": "http://localhost:8000",
  "operator_port": 8000,
  "node_port": 8001,
  "health_check_interval": 30,
  "health_check_timeout": 5
}
```

### Environment Variables (for Docker/production)

**Node Agent:**
- `NODE_ID` - Unique identifier for the node (default: hostname)
- `NODE_PORT` - Port for the node agent (default: 8001)
- `COORDINATOR_URL` - URL of the operator (default: from config.json)
- `OLLAMA_HOST` - Ollama API endpoint (default: http://localhost:11434)

**Operator:**
- `operator_port` - Port for the operator (default: 8000)

## API Reference

### Operator Endpoints

#### `POST /register`
Register a node with its available models.

**Request:**
```json
{
  "node_id": "mourad-laptop",
  "url": "http://192.168.1.20:8001",
  "models": ["llama3", "mistral"]
}
```

**Response:**
```json
{
  "status": "registered",
  "node_id": "mourad-laptop",
  "models": ["llama3", "mistral"]
}
```

#### `GET /nodes`
List all registered nodes.

**Response:**
```json
{
  "nodes": [
    {
      "node_id": "node1",
      "url": "http://node1:8001",
      "models": ["llama3"],
      "last_seen": "2025-01-15T10:30:00"
    }
  ]
}
```

#### `POST /inference`
Run an inference request.

**Request:**
```json
{
  "model": "llama3",
  "prompt": "Explain quantum entanglement"
}
```

**Response:** (Streamed JSON lines)
```json
{"token": "Quantum", "done": false}
{"token": " entanglement", "done": false}
{"token": " is", "done": false}
...
{"done": true}
```

### Node Agent Endpoints

#### `POST /run`
Execute an inference job (called by operator).

**Request:**
```json
{
  "job_id": "job-123",
  "prompt": "Explain quantum entanglement"
}
```

**Response:** Streamed JSON lines (same format as `/inference`)

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "node_id": "node1",
  "models": ["llama3", "mistral"]
}
```

#### `GET /models`
List available models on this node.

**Response:**
```json
{
  "node_id": "node1",
  "models": ["llama3", "mistral"]
}
```

## Client CLI Usage

```bash
# Basic inference (infer is the default command)
python client.py "Your prompt here" --model llama3

# Explicitly use infer command (optional)
python client.py infer "Your prompt here" --model llama3

# Specify custom operator
python client.py "Your prompt" --model llama3 --operator http://remote-host:8000

# List nodes
python client.py nodes

# List nodes on remote operator
python client.py nodes --operator http://remote-host:8000

# Get help
python client.py --help
```

## Development & Testing

### Manual Testing

1. Start operator
2. Start one or more node agents (on different ports)
3. Verify registration: `python client.py nodes`
4. Run inference: `python client.py "test prompt" --model llama3`

### Testing with Multiple Nodes

**Terminal 1:** Operator
```bash
python server.py
```

**Terminal 2:** Node 1
```bash
NODE_ID=node1 NODE_PORT=8001 python node.py
```

**Terminal 3:** Node 2
```bash
NODE_ID=node2 NODE_PORT=8002 python node.py
```

**Terminal 4:** Client
```bash
python client.py "Explain distributed systems" --model llama3
python client.py nodes
```

## Troubleshooting

### "No node available with model: X"
- Ensure Ollama is running: `ollama serve`
- Verify models are installed: `ollama list`
- Check node registration: `python client.py nodes`

### Node fails to register
- Verify operator is running
- Check `COORDINATOR_URL` matches operator address
- Review operator logs

### Docker containers can't access Ollama
- Ensure Ollama is running on host
- On Linux, you may need to use your host IP instead of `host.docker.internal`
- Try: `OLLAMA_HOST=http://172.17.0.1:11434` (Docker bridge IP)

## Architecture Details

### Streaming Protocol

The system uses **JSON Lines** (newline-delimited JSON) for streaming:

```json
{"token": "Hello", "done": false}
{"token": " world", "done": false}
{"done": true}
```

Or on error:
```json
{"error": "Model not found", "done": true}
```

### Node Selection

The operator uses **round-robin** selection among nodes that have the requested model. This ensures:
- Even load distribution
- Simple, predictable routing
- No single node becomes a bottleneck

### Health Checks

- Health checks run every 30 seconds (configurable)
- Nodes not responding for 60 seconds are pruned
- Each successful health check updates the node's `last_seen` timestamp

## Roadmap

### Future Enhancements

- [ ] Crypto settlement (Openfort / Arbitrum integration)
- [ ] Persistent storage (PostgreSQL / Redis)
- [ ] Job receipts and completion tracking
- [ ] Node reputation system
- [ ] Authentication (API keys / wallet signatures)
- [ ] Peer discovery and NAT traversal
- [ ] Model-specific routing
- [ ] Request queuing and prioritization
- [ ] Performance metrics and monitoring

## License

MIT

## Contributing

This is an MVP. Contributions welcome!

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a pull request
