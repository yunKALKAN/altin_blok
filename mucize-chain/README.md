# Mucize Chain — OP Stack L2 Rollup

**EVM-uyumlu Layer 2 Rollup — mucizeWORK Ekosistemi**

## Zincir Bilgileri

| Parametre | Değer |
|-----------|-------|
| **Zincir Adı** | Mucize Chain |
| **Chain ID** | `481` (0x1E1) |
| **Native Token** | MZC (MucizeCoin) |
| **Block Time** | 2 saniye |
| **Settlement** | Ethereum (Sepolia → Mainnet) |
| **Data Availability** | Ethereum (calldata / EIP-4844 blobs) |
| **Framework** | OP Stack (Optimism) |
| **EVM Uyumluluğu** | %100 |

## Mimari

```
┌─────────────────────────────────────────────────┐
│              Mucize Chain (L2)                   │
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │  op-geth  │  │  op-node  │  │  op-batch  │  │
│  │(execution)│  │(consensus)│  │ (data→L1)  │  │
│  └───────────┘  └───────────┘  └───────────┘  │
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │op-proposer│  │ Blockscout│  │  Foundry   │  │
│  │(state→L1) │  │ (explorer)│  │  (deploy)  │  │
│  └───────────┘  └───────────┘  └───────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ Batched tx data + State roots
                       ▼
┌─────────────────────────────────────────────────┐
│          Ethereum L1 (Settlement)               │
│   OptimismPortal | SystemConfig | DisputeGame   │
└─────────────────────────────────────────────────┘
```

## Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose v2+
- Node.js 20+
- Foundry (Forge + Cast)
- ~0.5 Sepolia ETH (L1 kontrat deploy için)

### Kurulum

```bash
chmod +x setup.sh
./setup.sh
```

### Manuel Kurulum

```bash
# 1. Çevre değişkenlerini ayarla
cp .env.example .env
# .env dosyasını düzenle

# 2. Docker başlat
docker compose up -d

# 3. Sağlık kontrolü
curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
```

## RPC Endpoint'leri

| Servis | URL | Açıklama |
|--------|-----|----------|
| L2 RPC (HTTP) | `http://localhost:8545` | Ana JSON-RPC |
| L2 RPC (WS) | `ws://localhost:8546` | WebSocket |
| op-node | `http://localhost:8547` | Rollup node API |
| Explorer | `http://localhost:4000` | Blockscout |

## MetaMask'a Ekleme

```json
{
  "chainId": "0x1E1",
  "chainName": "Mucize Chain",
  "nativeCurrency": {
    "name": "MucizeCoin",
    "symbol": "MZC",
    "decimals": 18
  },
  "rpcUrls": ["http://localhost:8545"],
  "blockExplorerUrls": ["http://localhost:4000"]
}
```

## Foundry ile Deploy

```bash
cd foundry-test
forge build
forge script script/Deploy.s.sol \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY \
  --broadcast -vvvv
```

## Cast ile Test

```bash
cast chain-id --rpc-url http://localhost:8545
cast block-number --rpc-url http://localhost:8545
cast client --rpc-url http://localhost:8545
```

---

**Mimar Yonus KALKAN — mucizeWORK Ekosistemi**
