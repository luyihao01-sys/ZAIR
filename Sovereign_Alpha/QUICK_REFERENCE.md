# Quick Command Reference

## 🚀 Setup

```bash
# Clone/enter project
cd Sovereign_Alpha

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Ollama (macOS/Linux)
curl https://ollama.ai/install.sh | sh

# Install Ollama (Windows)
# Download from https://ollama.ai

# Download LLM model
ollama pull llama3
# Alternative models: ollama pull hermes, mistral, neural-chat
```

---

## 📦 Install Dependencies

```bash
# Miner
cd zair-miner
pip install -r requirements.txt

# Validator (in another terminal)
cd zair-validator
pip install -r requirements.txt
```

---

## ⚙️ Configuration

```bash
# Create .env files
cp zair-miner/.env.example zair-miner/.env
cp zair-validator/.env.example zair-validator/.env

# Edit with your private key
nano zair-miner/.env
# Set: ETHEREUM_PRIVATE_KEY=0x1234567890abcdef...
```

---

## 🏃 Running Services

### Terminal 1: Ollama Server
```bash
# Start Ollama daemon
ollama serve

# In another window, verify it's running
curl http://localhost:11434/api/tags

# List available models
ollama list
```

### Terminal 2: Validator API
```bash
cd zair-validator
python -m uvicorn src.api:app --reload --port 8001

# Test it
curl http://localhost:8001/health
# Response: {"status": "healthy", "timestamp": "..."}
```

### Terminal 3: Miner
```bash
cd zair-miner
python src/miner.py --node-name Node_Dubai --region MEA
```

### Terminal 4: Run Tests
```bash
python test_integration.py
```

---

## 📡 API Calls

### Submit Risk Vector (with Signature)
```bash
curl -X POST http://localhost:8001/submit_inference \
  -H "Content-Type: application/json" \
  -d '{
    "vector": {
      "node_name": "Node_Dubai",
      "asset_id": "RWA-001",
      "timestamp": "2026-05-18T12:34:56Z",
      "legal_risk": 35.5,
      "liquidity_risk": 42.0,
      "smart_contract_risk": 28.5,
      "counterparty_risk": 31.0,
      "yield_sustainability": 75.5,
      "composite_risk_score": 38.2,
      "confidence_level": 82.5,
      "regional_sentiment": "neutral",
      "local_data_signals": {}
    },
    "signature": "0x1234567890abcdef...",
    "signer_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f42e",
    "submission_time": "2026-05-18T12:34:57Z"
  }'
```

### Health Check
```bash
curl http://localhost:8001/health
```

### Get Network Status
```bash
curl http://localhost:8001/network_status
```

### Get Leaderboard
```bash
curl http://localhost:8001/leaderboard?top_n=10
```

### Get Consensus (After Processing)
```bash
curl http://localhost:8001/consensus/RWA-001
```

### Process Asset
```bash
curl -X POST "http://localhost:8001/process_asset?asset_id=RWA-001&asset_name=Dubai_Fund&actual_stability=true"
```

---

## 🧪 Testing

### Full Integration Test
```bash
python test_integration.py
```

This script:
- ✅ Tests Ollama connectivity
- ✅ Runs real AI inference
- ✅ Generates EIP-712 signature
- ✅ Creates submission payload
- ✅ Submits to validator
- ✅ Validates entire flow

### Test Ollama Directly
```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "prompt": "What is the composite risk of a real estate fund?",
    "stream": false,
    "temperature": 0.3
  }'
```

### Verify Signature Generation
```python
python -c "
from eth_account import Account
account = Account.create()
print(f'Private Key: {account.key.hex()}')
print(f'Public Address: {account.address}')
"
```

---

## 🔍 Debugging

### Check Ollama
```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# List models
ollama list

# Download model if missing
ollama pull llama3

# Check logs
ollama serve  # See output directly
```

### Check Validator
```bash
# Is validator running?
curl http://localhost:8001/health

# Check logs
# Look for "✓ Vector accepted" messages
# Look for "✗ Invalid signature" errors
```

### Check Miner Logs
```bash
# Look for:
# ✓ Ollama inference completed
# ✓ Vector signed successfully
# ✓ Vector submitted successfully
```

---

## 📋 File Structure

```
Sovereign_Alpha/
├── zair-miner/
│   ├── src/
│   │   ├── miner.py          ← Real AI + EIP-712 signing
│   │   └── __init__.py
│   ├── requirements.txt
│   └── .env.example
├── zair-validator/
│   ├── src/
│   │   ├── validator.py       ← Consensus aggregation
│   │   ├── api.py             ← FastAPI + signature verification
│   │   └── __init__.py
│   ├── requirements.txt
│   └── .env.example
├── zair-contracts/
│   └── ...
├── openapi.yaml               ← OpenAPI specification
├── API_SPECIFICATION.md        ← Detailed API docs
├── INTEGRATION_GUIDE.md        ← How to integrate
├── MIGRATION_SUMMARY.md        ← What changed
├── test_integration.py         ← Comprehensive test
└── README.md
```

---

## 🎯 Common Issues

### "Connection refused" to Ollama
```bash
# Make sure Ollama is running
ollama serve

# Check it's accessible
curl http://localhost:11434/api/tags
```

### "Invalid signature"
```bash
# Check private key format
# Should be: 0x1234567890abcdef... (66 chars total with 0x)

# Verify key isn't corrupted
python -c "
from eth_account import Account
key = '0x1234567890abcdef...'
account = Account.from_key(key)
print(account.address)
"
```

### "Model not found"
```bash
# List available models
ollama list

# Download if missing
ollama pull llama3
ollama pull hermes
ollama pull mistral
```

### "Validator not running"
```bash
cd zair-validator
pip install -r requirements.txt
python -m uvicorn src.api:app --reload --port 8001
```

---

## 🔑 Private Key Management

### Generate Test Key
```python
from eth_account import Account
account = Account.create()
print(account.key.hex())      # Private key
print(account.address)         # Public address
```

### Load Existing Key
```python
from eth_account import Account
key = "0x1234567890abcdef..."
account = Account.from_key(key)
print(account.address)
```

### Never Do This! 🚫
```python
# DON'T commit private keys
# DON'T hardcode in scripts
# DON'T share with anyone
# DON'T post on GitHub
# DO use .env files
# DO rotate regularly
# DO use hardware wallets for mainnet
```

---

## 📊 Monitoring

### Real-time Validator Stats
```bash
# Watch network status
watch -n 5 'curl -s http://localhost:8001/network_status | python -m json.tool'

# Watch leaderboard
watch -n 10 'curl -s http://localhost:8001/leaderboard | python -m json.tool'
```

### Check Training Data
```bash
# View training dataset
ls -lh zair-validator/training_dataset.jsonl

# Count records
wc -l zair-validator/training_dataset.jsonl

# Sample first record
head -1 zair-validator/training_dataset.jsonl | python -m json.tool
```

---

## 🚀 Production Deployment

### Environment Variables (Secure)
```bash
# Never in .env, use secrets management
export ETHEREUM_PRIVATE_KEY=...
export VALIDATOR_URL=...
export OLLAMA_HOST=...
```

### Docker (Optional)
```bash
# Build miner Docker image
docker build -f zair-miner/Dockerfile -t zair-miner:latest .

# Build validator Docker image
docker build -f zair-validator/Dockerfile -t zair-validator:latest .

# Run with compose
docker-compose up -d
```

### Systemd Service (Linux)
```bash
# Create service file
sudo nano /etc/systemd/system/zair-validator.service

# Content:
[Unit]
Description=Zair Validator
After=network.target

[Service]
Type=simple
User=zair
WorkingDirectory=/home/zair/Sovereign_Alpha
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/zair/Sovereign_Alpha/venv/bin/python -m uvicorn src.api:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable zair-validator
sudo systemctl start zair-validator
sudo systemctl status zair-validator
```

---

## 📞 Support

- **GitHub Issues:** https://github.com/zairprotocol/validator/issues
- **Discord:** https://discord.gg/zairprotocol
- **Email:** support@zairprotocol.com
- **Docs:** See `INTEGRATION_GUIDE.md`

---

## ✅ Verification Checklist

Before going live:

- [ ] Ollama running with model downloaded
- [ ] Private key loaded and tested
- [ ] Validator API accessible on correct port
- [ ] Test submission successful (202 Accepted)
- [ ] Signature verification working
- [ ] Consensus aggregation working
- [ ] PoA rewards distributing
- [ ] Training data recording
- [ ] Monitoring in place
- [ ] Backups configured

---

## 🎓 Next Steps

1. **Understand the architecture:** Read `INTEGRATION_GUIDE.md`
2. **Review the API:** Check `API_SPECIFICATION.md`
3. **Run the test:** Execute `test_integration.py`
4. **Monitor logs:** Watch validator and miner output
5. **Process assets:** Call `/process_asset` endpoint
6. **Check results:** View consensus and leaderboard
7. **Deploy to production:** Follow deployment guide
