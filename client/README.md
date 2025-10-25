# ODLA Client

Command-line tool to send AI inference requests to the ODLA distributed network.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.json` to point to your server:

```json
{
  "operator_url": "http://your-server-ip:8000",
  "payment_service_url": "http://localhost:3000"
}
```

## Usage

### Basic Inference

```bash
# Simple query (test mode, no payment)
python client.py "What is 2+2?" --model llama3 --test

# With specific model
python client.py "Explain quantum physics" --model llama3

# Using phi model
python client.py "What is the capital of France?" --model phi
```

### List Available Nodes

```bash
python client.py nodes
```

### Payment Setup

To enable automatic payments, set your Concordium wallet credentials:

```bash
export CONCORDIUM_SENDER_KEY='your_private_key_hex'
export CONCORDIUM_SENDER_ADDRESS='4nB44...'
```

Or use a `.env.local` file:

```bash
source .env.local
```

### Test Mode (No Payment)

Use `--test` flag to skip payment requirement:

```bash
python client.py "your prompt" --model llama3 --test
```

## Examples

```bash
# Test inference without payment
python client.py "in what country is London?" --model phi --test

# Production inference with automatic payment
python client.py "Write a haiku about AI" --model llama3

# Check available nodes
python client.py nodes
```

## Troubleshooting

### Python 3.13 Compatibility

If you see errors like `TypeError: TyperArgument.make_metavar()`, upgrade typer:

```bash
pip install --upgrade typer>=0.12.0
```

### Connection Errors

Make sure the server is running and accessible:

```bash
curl http://your-server-ip:8000/health
```
