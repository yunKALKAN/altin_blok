#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════
# MUCIZE CHAIN — MASTER SETUP
# OP Stack + Foundry + Blockscout
# Mimar: Yonus KALKAN — mucizeWORK Ekosistemi
# ═══════════════════════════════════════════════

export CHAIN_NAME="Mucize Chain"
export CHAIN_ID=481
export NATIVE_TOKEN="MZC"
export BLOCK_TIME=2

echo "══════════════════════════════════════════"
echo "  MUCIZE CHAIN — Master Setup"
echo "  Chain ID: $CHAIN_ID | Token: $NATIVE_TOKEN"
echo "══════════════════════════════════════════"

# ──────────────────────────────────────────────
# SYSTEM UPDATE
# ──────────────────────────────────────────────

echo "[1/7] Sistem güncelleniyor..."
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  curl wget git jq make gcc g++ unzip \
  docker.io docker-compose build-essential

# ──────────────────────────────────────────────
# NODE.js
# ──────────────────────────────────────────────

echo "[2/7] Node.js kuruluyor..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs
fi
echo "Node: $(node -v) | npm: $(npm -v)"

# ──────────────────────────────────────────────
# FOUNDRY
# ──────────────────────────────────────────────

echo "[3/7] Foundry kuruluyor..."
if ! command -v forge &>/dev/null; then
  curl -L https://foundry.paradigm.xyz | bash
  export PATH="$HOME/.foundry/bin:$PATH"
  foundryup
fi
echo "Forge: $(forge --version)"

# ──────────────────────────────────────────────
# PROJECT DIRECTORY
# ──────────────────────────────────────────────

echo "[4/7] Proje dizini hazırlanıyor..."
CHAIN_DIR="${CHAIN_DIR:-$HOME/mucize-chain}"
mkdir -p "$CHAIN_DIR"
cd "$CHAIN_DIR"

# ──────────────────────────────────────────────
# ENV CONFIG
# ──────────────────────────────────────────────

if [ ! -f .env ]; then
  echo "[4b] .env dosyası oluşturuluyor..."
  cat > .env <<EOF
# ═══ MUCIZE CHAIN — ENV ═══
L1_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
L1_BEACON_URL=https://ethereum-sepolia-beacon-api.publicnode.com
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
CHAIN_NAME=MucizeChain
L2_CHAIN_ID=481
BLOCK_TIME=2
GAS_LIMIT=30000000
BLOCKSCOUT_ENABLED=true
BLOCKSCOUT_PORT=4000
EOF
  echo "⚠  .env dosyasını düzenle: $CHAIN_DIR/.env"
fi

# ──────────────────────────────────────────────
# DOCKER COMPOSE
# ──────────────────────────────────────────────

echo "[5/7] Docker Compose hazırlanıyor..."
cat > docker-compose.yml <<'COMPOSE'
version: '3.9'

services:
  op-geth:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-geth:v1.101511.1
    container_name: mucize-op-geth
    restart: unless-stopped
    ports:
      - "8545:8545"
      - "8546:8546"
    command: >
      --http
      --http.addr 0.0.0.0
      --http.vhosts '*'
      --http.corsdomain '*'
      --http.api eth,net,web3,debug,txpool,admin
      --ws
      --ws.addr 0.0.0.0
      --ws.origins '*'
      --ws.api eth,net,web3,debug,txpool,admin
      --syncmode full
      --gcmode archive
    volumes:
      - chaindata:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8545 --post-data='{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}' --header='Content-Type: application/json' | grep -q 'result'"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 15s

  op-node:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:v1.13.5
    container_name: mucize-op-node
    restart: unless-stopped
    depends_on:
      op-geth:
        condition: service_healthy
    ports:
      - "8547:8547"
      - "9003:9003"

  blockscout:
    image: blockscout/blockscout:latest
    container_name: mucize-explorer
    restart: unless-stopped
    environment:
      - ETHEREUM_JSONRPC_VARIANT=geth
      - ETHEREUM_JSONRPC_HTTP_URL=http://op-geth:8545
      - ETHEREUM_JSONRPC_WS_URL=ws://op-geth:8546
    ports:
      - "4000:4000"
    profiles:
      - explorer

volumes:
  chaindata:
    name: mucize_chain_data
COMPOSE

# ──────────────────────────────────────────────
# START DOCKER
# ──────────────────────────────────────────────

echo "[6/7] Docker başlatılıyor..."
sudo systemctl enable docker
sudo systemctl start docker
sudo docker compose up -d

# ──────────────────────────────────────────────
# FOUNDRY TEST PROJECT
# ──────────────────────────────────────────────

echo "[7/7] Foundry test projesi hazırlanıyor..."
if [ ! -d foundry-test ]; then
  mkdir -p foundry-test
  cd foundry-test
  forge init --no-commit

  cat > src/MZCCounter.sol <<'SOL'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MZCCounter {
    string public constant CHAIN = "Mucize Chain";
    uint256 public number;

    function setNumber(uint256 n) external {
        number = n;
    }

    function increment() external {
        number++;
    }
}
SOL

  mkdir -p script
  cat > script/Deploy.s.sol <<'DEPLOY'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/MZCCounter.sol";

contract Deploy is Script {
    function run() external {
        vm.startBroadcast();
        MZCCounter counter = new MZCCounter();
        console2.log("MZC Counter deployed:", address(counter));
        vm.stopBroadcast();
    }
}
DEPLOY

  forge build
  cd ..
fi

# ──────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────

echo ""
echo "Sağlık kontrolü bekleniyor (15s)..."
sleep 15

HEALTH=$(curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' 2>/dev/null || echo "OFFLINE")

echo ""
echo "══════════════════════════════════════════"
echo "  MUCIZE CHAIN — SETUP TAMAMLANDI"
echo "══════════════════════════════════════════"
echo "  RPC:        http://localhost:8545"
echo "  WS:         ws://localhost:8546"
echo "  Explorer:   http://localhost:4000"
echo "  Chain ID:   $CHAIN_ID (0x1E1)"
echo "  Token:      $NATIVE_TOKEN (MucizeCoin)"
echo "  Block Time: ${BLOCK_TIME}s"
echo "  Health:     $HEALTH"
echo "══════════════════════════════════════════"
echo "  Mimar Yonus KALKAN — mucizeWORK"
echo "══════════════════════════════════════════"
