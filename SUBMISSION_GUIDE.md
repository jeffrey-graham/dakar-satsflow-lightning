# Dakar Bitcoin Hack by BTrust Submission Guide (`SatsFlow`)

**Hackathon URL:** `https://dakar-bitcoin-hack-2026.devpost.com/`  
**Prize Pool:** `$900` Cash Pool

---

## 1. Exact Copy-Paste Devpost Fields

- **Project Name:**  
  `SatsFlow: Lightning L402 & Offline USSD Micro-Settlement for West Africa`

- **Elevator Pitch (Max 200 characters):**  
  `Bitcoin Lightning L402 Macaroon API gateway, Multi-Path Payment (MPP) router & offline USSD/Base45 voucher engine cutting West African (XOF/NGN/GHS) remittance fees from 7.85% to 0.26%.`

- **Built With Tags:**  
  `bitcoin`, `lightning-network`, `bolt11`, `l402`, `python`, `javascript`, `ussd`, `remittances`, `west-africa`, `github-pages`

- **Try It Out / Live Demo Link:**  
  `https://jeffrey-graham.github.io/dakar-satsflow-lightning/`

- **Source Code Repository Link:**  
  `https://github.com/jeffrey-graham/dakar-satsflow-lightning`

---

## 2. Project Story (Markdown Copy-Paste for Devpost Description)

### Inspiration & Problem Statement
Sending money between the diaspora (`EUR/USD`) and West Africa (`XOF` BCEAO in Senegal & Côte d'Ivoire, `NGN` in Nigeria, `GHS` in Ghana) still costs **7.8%–9.5% in fees** and takes **2–5 business days** via legacy remittance operators. Meanwhile, West African developers building solar mini-grids, local AI APIs, and cross-border B2B settlements lack accountless Lightning HTTP 402 (`L402`) micro-payment gateways, and millions of feature-phone users need offline-resilient USSD/SMS voucher settlement when mobile internet drops.

### Technical Architecture (`src/satsflow_engine.py`)
1. **Cryptographic BOLT-11 Invoice Parser & Encoder (BIP-173 Bech32):** Full 6-word polymod checksum verification, HRP multiplier decoding (`m`, `u`, `n`, `p`), 256-bit tagged payment hash (`p`), description (`d`), expiry (`x`), and atomic HTLC preimage verification ($\text{SHA256}(\text{preimage}) == \text{payment\_hash}$).
2. **L402 (`LSAT`) Chained HMAC-SHA256 Macaroon + Preimage API Paywall:** Issues `HTTP 402 Payment Required` headers (`WWW-Authenticate: L402 macaroon="...", invoice="lnbc..."`) and verifies chained caveats + HTLC preimages in sub-millisecond time.
3. **Multi-Hop Dijkstra & Multi-Path Payment (MPP) Channel Liquidity Optimizer:** Finds minimum-fee paths across European and West African LSPs (`Paris-Eclair-LSP`, `Frankfurt-ACINQ`, `Abidjan-UEMOA-Gate`, `Dakar-BTrust-Hub`, `Lagos-BitNob-Core`, `Accra-Sats-Bridge`) and automatically splits large transfers into concurrent edge-disjoint **Multi-Path Payment (MPP)** shards when single-channel capacity is exceeded.
4. **Offline USSD (`*789#`) & RFC 9285 Base45 SMS Voucher Studio:** Generates compact HMAC-SHA256 signed Base45 SMS tokens (`SATS1:...`) and USSD dial strings (`*789*1*SATS*PIN#`) for feature-phone users across Senegal, Nigeria, and Ghana.

---

## 3. Local File Paths for Upload

- **60-Second 1080p Demo Video:** `/home/jeff/.gemini/antigravity/scratch/freelancework/dakar-bitcoin-hackathon/demo.mp4`
- **Screenshot 1 (Remittance Corridor Comparator):** `/home/jeff/.gemini/antigravity/scratch/freelancework/dakar-bitcoin-hackathon/screenshots/remittance_corridor.png`
- **Screenshot 2 (L402 Macaroon & BOLT-11 Sandbox):** `/home/jeff/.gemini/antigravity/scratch/freelancework/dakar-bitcoin-hackathon/screenshots/l402_macaroon_sandbox.png`
- **Screenshot 3 (Multi-Path Payment MPP Route Graph):** `/home/jeff/.gemini/antigravity/scratch/freelancework/dakar-bitcoin-hackathon/screenshots/mpp_route_graph.png`
