# ODLA Payment Service

Concordium blockchain payment integration for ODLA distributed AI inference network.

## Features

- **PLT Stablecoin Payments**: Uses Concordium Protocol-Level Tokens (no smart contracts, more secure)
- **Supported Coins**: USDR, EURR, eUSD, eEUR, eGBP, eSGD, VEUR, VCHF, VGBP
- **Real Liquidity**: USDR/EURR listed on 50+ exchanges with €3B+ transaction volume
- **Automatic**: Payments processed automatically after AI inference completes

## Why PLT Stablecoins?

PLT (Protocol-Level Tokens) are native to Concordium blockchain:
- No smart contracts needed for transfers (fewer attack vectors)
- Better security than traditional ERC-20 tokens
- Real-world adoption: listed on Kraken, Bitfinex, Bybit, HTX
- Perfect for PayFi use cases like AI inference billing

## Installation

```bash
cd payment-service
npm install
cp .env.example .env
```

## Configuration

Edit `.env`:

```bash
PORT=3000
CONCORDIUM_NODE=https://grpc.testnet.concordium.com:20000
NETWORK_ID=100  # 100 = testnet, 1 = mainnet
```

## Running

```bash
# Development
npm run dev

# Production
npm start
```

## API Endpoints

### POST /pay

Send CCD or PLT stablecoin payment.

**Request:**
```json
{
  "amount": 1.5,
  "recipient": "3sXyPRjb9ZZjZ5pKqT1xKBZ9BvXZQxVqXqXqXqX",
  "memo": "job-123",
  "sender_key": "your_private_key_hex",
  "sender_address": "3sAbc..."
}
```

**Response:**
```json
{
  "success": true,
  "transaction_hash": "abc123...",
  "amount": 1.5,
  "recipient": "3sXy...",
  "memo": "job-123",
  "explorer_url": "https://testnet.ccdscan.io/transactions/abc123..."
}
```

### GET /balance/:address

Check account balance.

**Example:**
```bash
curl http://localhost:3000/balance/3sXyPRjb9ZZjZ5pKqT1xKBZ9BvXZQxVqXqXqXqX
```

### GET /transaction/:hash

Get transaction status.

**Example:**
```bash
curl http://localhost:3000/transaction/abc123...
```

### GET /health

Service health check.

## Wallet Setup

1. **Install Concordium Wallet**
   - Download mobile app or browser extension
   - Create new account on testnet
   - Fund account from [CCD Testnet Faucet](https://testnet.ccdscan.io)

2. **Export Private Key**
   - From wallet, export account keys
   - Save private key (hex string)
   - Save account address (starts with "3s...")

3. **Configure Client**
   - Set environment variables for automatic payments:
     ```bash
     export CONCORDIUM_SENDER_KEY="your_private_key_hex"
     export CONCORDIUM_SENDER_ADDRESS="3sXy..."
     ```

## Testing

```bash
# Check service health
curl http://localhost:3000/health

# Send test payment (replace with your keys)
curl -X POST http://localhost:3000/pay \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 0.001,
    "recipient": "3sXy...",
    "memo": "test-job",
    "sender_key": "your_private_key_hex",
    "sender_address": "3sAbc..."
  }'

# Check account balance
curl http://localhost:3000/balance/3sXy...
```

## Integration with ODLA

The Python client (`client.py`) calls this service automatically after inference completes:

```python
# After inference, client.py automatically calls payment service
payment_payload = {
    "amount": payment_amount,
    "recipient": node_address,
    "memo": job_id,
    "sender_key": os.getenv("CONCORDIUM_SENDER_KEY"),
    "sender_address": os.getenv("CONCORDIUM_SENDER_ADDRESS")
}

response = await client.post(
    f"{payment_service_url}/pay",
    json=payment_payload
)
```

## Environment Variables

Client-side (for `client.py`):
```bash
export CONCORDIUM_SENDER_KEY="your_private_key_hex"
export CONCORDIUM_SENDER_ADDRESS="3sXy..."
```

These credentials are passed to the payment service for each transaction.

## Resources

- [Concordium Web SDK](https://github.com/Concordium/concordium-node-sdk-js)
- [PLT Stablecoins](https://www.concordium.com/article/10-new-stablecoins-5-currencies-the-explosive-growth-of-the-concordium-mainnet)
- [Concordium Testnet Explorer](https://testnet.ccdscan.io/)
