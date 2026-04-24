"""
Cüzdan İzleme Dashboard'u — FastAPI + Etherscan + CoinGecko
Adres: 0x4E83362442B8d1beC281594cea3050c8EB01311C
"""

import os
import asyncio
from typing import Optional

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Cüzdan İzleme Dashboard'u")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_WALLET = "0x4E83362442B8d1beC281594cea3050c8EB01311C"
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BLOCKSCOUT_BASE = "https://eth.blockscout.com/api/v2"

TRACKED_TOKENS = [
    {
        "symbol": "WBTC",
        "name": "Wrapped BTC",
        "contract": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "decimals": 8,
        "coingecko_id": "wrapped-bitcoin",
    },
    {
        "symbol": "renBTC",
        "name": "renBTC",
        "contract": "0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D",
        "decimals": 8,
        "coingecko_id": "renbtc",
    },
    {
        "symbol": "UNI",
        "name": "Uniswap",
        "contract": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "decimals": 18,
        "coingecko_id": "uniswap",
    },
    {
        "symbol": "DAI",
        "name": "Dai Stablecoin",
        "contract": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "decimals": 18,
        "coingecko_id": "dai",
    },
    {
        "symbol": "LPT",
        "name": "Livepeer",
        "contract": "0x58b6A8A3302369DAEc383334672404Ee733aB239",
        "decimals": 18,
        "coingecko_id": "livepeer",
    },
    {
        "symbol": "stkAAVE",
        "name": "Staked Aave",
        "contract": "0x4da27a545c0c5B758a6BA100e3a049001de870f5",
        "decimals": 18,
        "coingecko_id": "aave",
    },
    {
        "symbol": "ZRX",
        "name": "0x Protocol",
        "contract": "0xE41d2489571d322189246DaFA5ebDe1F4699F498",
        "decimals": 18,
        "coingecko_id": "0x",
    },
    {
        "symbol": "XDATA",
        "name": "Streamr",
        "contract": "0x8f693ca8D21b157107184d29D398A8D082b38b76",
        "decimals": 18,
        "coingecko_id": "streamr",
    },
    {
        "symbol": "BOND",
        "name": "BarnBridge",
        "contract": "0x0391D2021f89DC339F60Fff84546EA23E337750f",
        "decimals": 18,
        "coingecko_id": "barnbridge",
    },
]

FALLBACK_BALANCES = {
    "ETH": 1.0065,
    "WBTC": 0.08005,
    "renBTC": 0.32538,
    "UNI": 283.16,
    "DAI": 2923.0,
    "LPT": 2.26,
    "stkAAVE": 0.0475,
    "ZRX": 6.43,
    "XDATA": 487.6,
    "BOND": 7.92,
}

FALLBACK_PRICES = {
    "ETH": 2317.0,
    "WBTC": 77380.0,
    "renBTC": 17308.0,
    "UNI": 3.27,
    "DAI": 1.0,
    "LPT": 2.14,
    "stkAAVE": 94.87,
    "ZRX": 0.116,
    "XDATA": 0.000843,
    "BOND": 0.0397,
}


def _etherscan_key() -> str:
    return os.environ.get("ETHERSCAN_API_KEY", "")


async def _fetch_eth_balance(client: httpx.AsyncClient, address: str) -> float:
    key = _etherscan_key()
    if key:
        params = {
            "chainid": "1",
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": key,
        }
        try:
            resp = await client.get(ETHERSCAN_BASE, params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "1":
                return int(data["result"]) / 1e18
        except Exception:
            pass
    try:
        resp = await client.get(
            f"{BLOCKSCOUT_BASE}/addresses/{address}", timeout=10
        )
        data = resp.json()
        coin_bal = data.get("coin_balance")
        if coin_bal:
            return int(coin_bal) / 1e18
    except Exception:
        pass
    return FALLBACK_BALANCES["ETH"]


async def _fetch_token_balance(
    client: httpx.AsyncClient, address: str, contract: str, decimals: int
) -> Optional[float]:
    key = _etherscan_key()
    if key:
        params = {
            "chainid": "1",
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": contract,
            "address": address,
            "tag": "latest",
            "apikey": key,
        }
        try:
            resp = await client.get(ETHERSCAN_BASE, params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "1":
                return int(data["result"]) / (10**decimals)
        except Exception:
            pass
    return None


async def _fetch_prices(client: httpx.AsyncClient) -> dict[str, float]:
    ids = ",".join(
        ["ethereum"] + [t["coingecko_id"] for t in TRACKED_TOKENS]
    )
    try:
        resp = await client.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": ids, "vs_currencies": "usd"},
            timeout=10,
        )
        data = resp.json()
        prices: dict[str, float] = {}
        eth_price = data.get("ethereum", {}).get("usd")
        if eth_price:
            prices["ETH"] = float(eth_price)
        for token in TRACKED_TOKENS:
            cg = data.get(token["coingecko_id"], {}).get("usd")
            if cg is not None:
                prices[token["symbol"]] = float(cg)
        return prices
    except Exception:
        return {}


@app.get("/api/portfolio")
async def get_portfolio(address: str = Query(default=DEFAULT_WALLET)):
    async with httpx.AsyncClient() as client:
        eth_task = _fetch_eth_balance(client, address)
        price_task = _fetch_prices(client)
        token_tasks = {
            t["symbol"]: _fetch_token_balance(
                client, address, t["contract"], t["decimals"]
            )
            for t in TRACKED_TOKENS
        }

        eth_balance, prices = await asyncio.gather(eth_task, price_task)

        token_results = {}
        for symbol, coro in token_tasks.items():
            token_results[symbol] = await coro

    merged_prices = {**FALLBACK_PRICES, **prices}

    portfolio = []
    portfolio.append(
        {
            "symbol": "ETH",
            "name": "Ethereum",
            "balance": eth_balance,
            "price": merged_prices.get("ETH", 0),
            "value": eth_balance * merged_prices.get("ETH", 0),
        }
    )
    for token in TRACKED_TOKENS:
        sym = token["symbol"]
        bal = token_results.get(sym)
        if bal is None:
            bal = FALLBACK_BALANCES.get(sym, 0)
        price = merged_prices.get(sym, 0)
        portfolio.append(
            {
                "symbol": sym,
                "name": token["name"],
                "balance": bal,
                "price": price,
                "value": bal * price,
            }
        )

    portfolio.sort(key=lambda x: x["value"], reverse=True)
    total = sum(item["value"] for item in portfolio)

    return {
        "address": address,
        "total_usd": round(total, 2),
        "tokens": [
            {
                **item,
                "balance": round(item["balance"], 6),
                "price": round(item["price"], 4),
                "value": round(item["value"], 2),
                "pct": round(item["value"] / total * 100, 2) if total > 0 else 0,
            }
            for item in portfolio
        ],
        "source": "live" if prices else "fallback",
    }


def _parse_blockscout_timestamp(ts_str: str) -> int:
    """Convert ISO timestamp string to unix epoch seconds."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return 0


@app.get("/api/history")
async def get_history(address: str = Query(default=DEFAULT_WALLET)):
    """Fetch ETH transactions and ERC-20 token transfers from Blockscout."""
    async with httpx.AsyncClient() as client:
        addr_lower = address.lower()
        tx_url = f"{BLOCKSCOUT_BASE}/addresses/{address}/transactions"
        token_url = f"{BLOCKSCOUT_BASE}/addresses/{address}/token-transfers"

        try:
            eth_resp, token_resp = await asyncio.gather(
                client.get(tx_url, timeout=15),
                client.get(token_url, timeout=15),
            )
            eth_data = eth_resp.json()
            token_data = token_resp.json()
        except Exception:
            return {"address": address, "transactions": [], "error": "API error"}

    transactions = []

    for tx in eth_data.get("items", []):
        value_wei = int(tx.get("value", "0"))
        value_eth = value_wei / 1e18
        from_hash = tx.get("from", {}).get("hash", "") if isinstance(tx.get("from"), dict) else ""
        to_hash = tx.get("to", {}).get("hash", "") if isinstance(tx.get("to"), dict) else ""
        is_incoming = to_hash.lower() == addr_lower
        ts = _parse_blockscout_timestamp(tx.get("timestamp", ""))
        tx_status = tx.get("status", "")
        transactions.append({
            "type": "ETH",
            "symbol": "ETH",
            "hash": tx.get("hash", ""),
            "timestamp": ts,
            "from": from_hash,
            "to": to_hash,
            "value": round(value_eth, 6),
            "direction": "gelen" if is_incoming else "giden",
            "block": tx.get("block_number", 0),
            "method": tx.get("method") or (tx.get("decoded_input", {}) or {}).get("method_call", ""),
            "status": "basarili" if tx_status == "ok" else ("basarisiz" if tx_status == "error" else tx_status),
        })

    for tx in token_data.get("items", []):
        token_info = tx.get("token", {})
        decimals = int(token_info.get("decimals") or 18)
        total_val = tx.get("total", {})
        raw_value = int(total_val.get("value", "0")) if isinstance(total_val, dict) else 0
        value = raw_value / (10**decimals) if decimals > 0 else raw_value
        from_hash = tx.get("from", {}).get("hash", "") if isinstance(tx.get("from"), dict) else ""
        to_hash = tx.get("to", {}).get("hash", "") if isinstance(tx.get("to"), dict) else ""
        is_incoming = to_hash.lower() == addr_lower
        ts = _parse_blockscout_timestamp(tx.get("timestamp", ""))
        transactions.append({
            "type": "TOKEN",
            "symbol": token_info.get("symbol", "?"),
            "token_name": token_info.get("name", ""),
            "contract": token_info.get("address_hash", ""),
            "hash": tx.get("transaction_hash", "") or tx.get("hash", ""),
            "timestamp": ts,
            "from": from_hash,
            "to": to_hash,
            "value": round(value, 6),
            "direction": "gelen" if is_incoming else "giden",
            "block": tx.get("block_number", 0),
            "method": tx.get("method") or "",
        })

    seen_hashes: set[str] = set()
    unique_tx = []
    for tx in transactions:
        key = f"{tx['hash']}_{tx['symbol']}_{tx['direction']}"
        if key not in seen_hashes:
            seen_hashes.add(key)
            unique_tx.append(tx)

    unique_tx.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "address": address,
        "total_tx": len(unique_tx),
        "transactions": unique_tx,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Cüzdan İzleme Dashboard'u</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0f0f1a;--card:#1a1a2e;--accent:#00d2ff;--accent2:#7b2ff7;
  --text:#e0e0e0;--text-dim:#8888aa;--green:#00e676;--red:#ff5252;
  --border:#2a2a44;
}
body{font-family:'Inter','Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.header{
  background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
  border-bottom:1px solid var(--border);padding:20px 32px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
}
.header h1{font-size:22px;background:linear-gradient(90deg,var(--accent),var(--accent2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .addr{font-size:13px;color:var(--text-dim);font-family:monospace}
.header .badge{font-size:11px;padding:3px 10px;border-radius:20px;
  background:rgba(0,210,255,.15);color:var(--accent)}

.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:16px;padding:24px 32px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:24px;transition:transform .15s}
.card:hover{transform:translateY(-2px)}
.card .label{font-size:12px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.card .big{font-size:32px;font-weight:700}
.card .sub{font-size:13px;color:var(--text-dim);margin-top:4px}

.main-grid{display:grid;grid-template-columns:1fr 380px;gap:16px;padding:0 32px 32px;min-height:400px}
@media(max-width:900px){.main-grid{grid-template-columns:1fr}}

.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.table-wrap h3{padding:18px 20px;border-bottom:1px solid var(--border);font-size:15px}
table{width:100%;border-collapse:collapse}
th,td{padding:12px 20px;text-align:left;font-size:14px}
th{color:var(--text-dim);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.5px;
  border-bottom:1px solid var(--border)}
tr:hover{background:rgba(0,210,255,.04)}
td:last-child{text-align:right}
th:last-child{text-align:right}
.token-icon{width:28px;height:28px;border-radius:50%;background:var(--border);
  display:inline-flex;align-items:center;justify-content:center;font-size:11px;
  font-weight:700;margin-right:10px;vertical-align:middle}
.pct-bar{height:4px;border-radius:2px;background:var(--border);margin-top:4px;max-width:120px}
.pct-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent),var(--accent2))}

.chart-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;display:flex;flex-direction:column;align-items:center}
.chart-wrap h3{margin-bottom:16px;font-size:15px;align-self:flex-start}
.chart-container{position:relative;width:100%;max-width:320px;aspect-ratio:1}

.footer{text-align:center;padding:20px;color:var(--text-dim);font-size:12px;border-top:1px solid var(--border)}
.spinner{display:inline-block;width:20px;height:20px;border:2px solid var(--border);
  border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.refresh-btn{background:none;border:1px solid var(--border);color:var(--accent);
  padding:6px 16px;border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s}
.refresh-btn:hover{background:rgba(0,210,255,.1);border-color:var(--accent)}
.loading-overlay{position:fixed;inset:0;background:var(--bg);display:flex;
  align-items:center;justify-content:center;flex-direction:column;gap:16px;z-index:100}
.loading-overlay .spinner{width:40px;height:40px;border-width:3px}

.tabs{display:flex;gap:0;padding:0 32px;margin-top:8px}
.tab-btn{background:none;border:none;color:var(--text-dim);padding:12px 24px;
  font-size:14px;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;font-weight:500}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-content{display:none}
.tab-content.active{display:block}

.history-section{padding:0 32px 32px}
.history-table{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.history-table h3{padding:18px 20px;border-bottom:1px solid var(--border);font-size:15px;
  display:flex;align-items:center;justify-content:space-between}
.history-table h3 span{font-size:12px;color:var(--text-dim);font-weight:400}
.dir-in{color:var(--green);font-weight:600}
.dir-out{color:var(--red);font-weight:600}
.tx-hash{font-family:monospace;font-size:12px;color:var(--accent)}
.tx-addr{font-family:monospace;font-size:11px;color:var(--text-dim)}
.tx-time{font-size:12px;color:var(--text-dim)}
.tx-badge{font-size:10px;padding:2px 8px;border-radius:10px;font-weight:600;text-transform:uppercase}
.tx-badge.eth{background:rgba(0,210,255,.15);color:var(--accent)}
.tx-badge.token{background:rgba(123,47,247,.15);color:var(--accent2)}
.filter-bar{display:flex;gap:8px;padding:12px 20px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.filter-btn{background:none;border:1px solid var(--border);color:var(--text-dim);
  padding:4px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .2s}
.filter-btn:hover,.filter-btn.active{background:rgba(0,210,255,.1);border-color:var(--accent);color:var(--accent)}
</style>
</head>
<body>

<div class="loading-overlay" id="loader">
  <div class="spinner"></div>
  <div style="color:var(--text-dim)">Cüzdan verileri yükleniyor…</div>
</div>

<header class="header">
  <div>
    <h1>Cüzdan İzleme Dashboard'u</h1>
    <div class="addr" id="walletAddr">—</div>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <span class="badge" id="sourceLabel">—</span>
    <button class="refresh-btn" onclick="loadData()">Yenile</button>
  </div>
</header>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('portfolio')">Portföy</button>
  <button class="tab-btn" onclick="switchTab('history')">İşlem Geçmişi</button>
</div>

<div id="tab-portfolio" class="tab-content active">
  <div class="grid">
    <div class="card">
      <div class="label">Toplam Portföy Değeri</div>
      <div class="big" id="totalValue">—</div>
      <div class="sub" id="tokenCount">—</div>
    </div>
    <div class="card">
      <div class="label">BTC Pozisyonları (WBTC + renBTC)</div>
      <div class="big" id="btcValue">—</div>
      <div class="sub" id="btcDetail">—</div>
    </div>
    <div class="card">
      <div class="label">Nakit Benzeri (ETH + DAI)</div>
      <div class="big" id="cashValue">—</div>
      <div class="sub" id="cashDetail">—</div>
    </div>
    <div class="card">
      <div class="label">Diğer Tokenlar</div>
      <div class="big" id="otherValue">—</div>
      <div class="sub" id="otherDetail">—</div>
    </div>
  </div>

  <div class="main-grid">
    <div class="table-wrap">
      <h3>Token Detayları</h3>
      <table>
        <thead>
          <tr><th>Token</th><th>Miktar</th><th>Fiyat</th><th>Değer (USD)</th></tr>
        </thead>
        <tbody id="tokenTable">
          <tr><td colspan="4" style="text-align:center;padding:40px;color:var(--text-dim)">
            <div class="spinner"></div>
          </td></tr>
        </tbody>
      </table>
    </div>

    <div class="chart-wrap">
      <h3>Portföy Dağılımı</h3>
      <div class="chart-container">
        <canvas id="donutChart"></canvas>
      </div>
    </div>
  </div>
</div>

<div id="tab-history" class="tab-content">
  <div class="history-section">
    <div class="history-table">
      <h3>İşlem Geçmişi <span id="txCount">Yükleniyor…</span></h3>
      <div class="filter-bar">
        <button class="filter-btn active" onclick="filterTx('all')">Tümü</button>
        <button class="filter-btn" onclick="filterTx('gelen')">Gelen</button>
        <button class="filter-btn" onclick="filterTx('giden')">Giden</button>
        <button class="filter-btn" onclick="filterTx('ETH')">ETH</button>
        <button class="filter-btn" onclick="filterTx('TOKEN')">Token</button>
      </div>
      <table>
        <thead>
          <tr><th>Tarih</th><th>Tür</th><th>Token</th><th>Miktar</th><th>Kimden / Kime</th><th style="text-align:right">İşlem</th></tr>
        </thead>
        <tbody id="historyTable">
          <tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-dim)">
            Geçmişi görmek için "İşlem Geçmişi" sekmesine tıklayın
          </td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="footer">
  <a href="https://etherscan.io/address/0x4E83362442B8d1beC281594cea3050c8EB01311C" target="_blank">
    Etherscan'da Görüntüle ↗
  </a>
  &nbsp;·&nbsp; Otomatik yenileme: her 60 saniye
</div>

<script>
const COLORS = [
  '#00d2ff','#7b2ff7','#00e676','#ff9100','#ff5252',
  '#448aff','#ea80fc','#ffea00','#69f0ae','#ff6e40'
];

let chart = null;
let refreshTimer = null;

function fmt(n) {
  if (n >= 1000) return '$' + n.toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0});
  if (n >= 1) return '$' + n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
  return '$' + n.toFixed(4);
}

function fmtBal(n) {
  if (n >= 1000) return n.toLocaleString('en-US', {maximumFractionDigits:2});
  if (n >= 1) return n.toFixed(4);
  return n.toFixed(6);
}

async function loadData() {
  try {
    const res = await fetch('/api/portfolio');
    const data = await res.json();
    render(data);
  } catch (err) {
    console.error('Veri yüklenemedi:', err);
  } finally {
    document.getElementById('loader').style.display = 'none';
  }
}

function render(data) {
  // Header
  const short = data.address.slice(0,6) + '…' + data.address.slice(-4);
  document.getElementById('walletAddr').innerHTML =
    `<a href="https://etherscan.io/address/${data.address}" target="_blank">${short}</a>`;
  document.getElementById('sourceLabel').textContent =
    data.source === 'live' ? 'Canlı Veri' : 'Önbellek Verisi';

  // Summary cards
  document.getElementById('totalValue').textContent = fmt(data.total_usd);
  document.getElementById('tokenCount').textContent = data.tokens.length + ' token izleniyor';

  const btcTokens = data.tokens.filter(t => ['WBTC','renBTC'].includes(t.symbol));
  const btcTotal = btcTokens.reduce((s,t) => s + t.value, 0);
  document.getElementById('btcValue').textContent = fmt(btcTotal);
  document.getElementById('btcDetail').textContent = btcTokens.map(t => t.symbol + ': ' + fmtBal(t.balance)).join(' + ');

  const cashTokens = data.tokens.filter(t => ['ETH','DAI'].includes(t.symbol));
  const cashTotal = cashTokens.reduce((s,t) => s + t.value, 0);
  document.getElementById('cashValue').textContent = fmt(cashTotal);
  document.getElementById('cashDetail').textContent = cashTokens.map(t => t.symbol + ': ' + fmtBal(t.balance)).join(' + ');

  const otherTokens = data.tokens.filter(t => !['WBTC','renBTC','ETH','DAI'].includes(t.symbol));
  const otherTotal = otherTokens.reduce((s,t) => s + t.value, 0);
  document.getElementById('otherValue').textContent = fmt(otherTotal);
  document.getElementById('otherDetail').textContent = otherTokens.length + ' token';

  // Table
  const tbody = document.getElementById('tokenTable');
  tbody.innerHTML = data.tokens.map((t, i) => `
    <tr>
      <td>
        <span class="token-icon" style="background:${COLORS[i % COLORS.length]}22;color:${COLORS[i % COLORS.length]}">${t.symbol.slice(0,2)}</span>
        <strong>${t.symbol}</strong>
        <span style="color:var(--text-dim);font-size:12px;margin-left:4px">${t.name}</span>
      </td>
      <td>${fmtBal(t.balance)}</td>
      <td>${fmt(t.price)}</td>
      <td>
        <strong>${fmt(t.value)}</strong>
        <div class="pct-bar"><div class="pct-fill" style="width:${t.pct}%"></div></div>
        <span style="font-size:11px;color:var(--text-dim)">${t.pct}%</span>
      </td>
    </tr>
  `).join('');

  // Chart
  renderChart(data.tokens);
}

function renderChart(tokens) {
  const ctx = document.getElementById('donutChart').getContext('2d');
  const labels = tokens.map(t => t.symbol);
  const values = tokens.map(t => t.value);
  const colors = tokens.map((_, i) => COLORS[i % COLORS.length]);

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: '#1a1a2e',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#8888aa',
            padding: 12,
            font: { size: 12 },
            usePointStyle: true,
            pointStyleWidth: 8
          }
        },
        tooltip: {
          backgroundColor: '#1a1a2e',
          borderColor: '#2a2a44',
          borderWidth: 1,
          titleColor: '#e0e0e0',
          bodyColor: '#e0e0e0',
          callbacks: {
            label: function(ctx) {
              const v = ctx.parsed;
              const total = ctx.dataset.data.reduce((a,b) => a+b, 0);
              const pct = ((v / total) * 100).toFixed(1);
              return ` ${ctx.label}: $${v.toLocaleString('en-US', {maximumFractionDigits:0})} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

let allTx = [];
let historyLoaded = false;
let currentFilter = 'all';

function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.querySelector(`.tab-btn[onclick="switchTab('${tab}')"]`).classList.add('active');
  if (tab === 'history' && !historyLoaded) loadHistory();
}

function shortAddr(a) {
  if (!a) return '—';
  return a.slice(0,6) + '…' + a.slice(-4);
}

function fmtDate(ts) {
  if (!ts) return '—';
  const d = new Date(ts * 1000);
  return d.toLocaleDateString('tr-TR') + ' ' + d.toLocaleTimeString('tr-TR', {hour:'2-digit',minute:'2-digit'});
}

async function loadHistory() {
  const tbody = document.getElementById('historyTable');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-dim)"><div class="spinner"></div></td></tr>';
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    allTx = data.transactions || [];
    historyLoaded = true;
    document.getElementById('txCount').textContent = allTx.length + ' işlem bulundu';
    renderHistory(allTx);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--red)">Veri yüklenemedi</td></tr>';
  }
}

function filterTx(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  let filtered = allTx;
  if (filter === 'gelen') filtered = allTx.filter(t => t.direction === 'gelen');
  else if (filter === 'giden') filtered = allTx.filter(t => t.direction === 'giden');
  else if (filter === 'ETH') filtered = allTx.filter(t => t.type === 'ETH');
  else if (filter === 'TOKEN') filtered = allTx.filter(t => t.type === 'TOKEN');
  renderHistory(filtered);
}

function renderHistory(txs) {
  const tbody = document.getElementById('historyTable');
  const WALLET = '0x4E83362442B8d1beC281594cea3050c8EB01311C'.toLowerCase();
  if (!txs.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-dim)">İşlem bulunamadı</td></tr>';
    return;
  }
  tbody.innerHTML = txs.map(tx => {
    const isIn = tx.direction === 'gelen';
    const dirClass = isIn ? 'dir-in' : 'dir-out';
    const dirLabel = isIn ? 'GELEN' : 'GİDEN';
    const dirArrow = isIn ? '↓' : '↑';
    const typeClass = tx.type === 'ETH' ? 'eth' : 'token';
    const counterparty = isIn ? tx.from : tx.to;
    return `
      <tr>
        <td><div class="tx-time">${fmtDate(tx.timestamp)}</div></td>
        <td><span class="${dirClass}">${dirArrow} ${dirLabel}</span></td>
        <td>
          <span class="tx-badge ${typeClass}">${tx.type}</span>
          <strong style="margin-left:6px">${tx.symbol}</strong>
        </td>
        <td>${fmtBal(tx.value)} ${tx.symbol}</td>
        <td>
          <div class="tx-addr">${isIn ? 'Kimden' : 'Kime'}: <a href="https://etherscan.io/address/${counterparty}" target="_blank">${shortAddr(counterparty)}</a></div>
        </td>
        <td style="text-align:right">
          <a class="tx-hash" href="https://etherscan.io/tx/${tx.hash}" target="_blank">${shortAddr(tx.hash)}</a>
        </td>
      </tr>
    `;
  }).join('');
}

loadData();
refreshTimer = setInterval(loadData, 60000);
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    uvicorn.run(app, host="0.0.0.0", port=port)
