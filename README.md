# altin_blok — mucizeWORK Ekosistemi

Multi-chain kripto portföy takip ve komuta merkezi.

## Bileşenler

### Kasa Komuta Merkezi
```bash
python kasa_komuta_merkezi.py              # Terminal çıktısı
python kasa_komuta_merkezi.py --html       # HTML rapor
python kasa_komuta_merkezi.py --json       # JSON çıktı
python kasa_komuta_merkezi.py --all        # Hepsi
```

### Wallet Dashboard
```bash
pip install -r requirements.txt
python wallet_dashboard.py                 # FastAPI sunucusu → http://localhost:8000
```

### MZC Token (Smart Contracts)
```bash
cd contracts
npm install
npx hardhat compile
npx hardhat test                           # 26 test
npx hardhat run scripts/deploy.js --network sepolia   # Testnet deploy
```

### MZC Website
`website/` dizininde statik landing page ve whitepaper bulunur.

## MZC Token Özeti

| Özellik | Değer |
|---|---|
| Token Adı | MucizeCoin |
| Sembol | MZC |
| Standart | ERC-20 |
| Toplam Arz | 1,000,000,000 |
| Başlangıç Fiyatı | $0.01 |
| Zincirler | Ethereum, BNB Chain, Base, HyperEVM |

---

**Mimar Yonus KALKAN — mucizeWORK Ekosistemi**
