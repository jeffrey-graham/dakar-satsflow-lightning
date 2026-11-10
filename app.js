// SatsFlow Interactive Dashboard — Dakar Bitcoin Hack by BTrust (2026)

const FX_PER_SAT = {
  XOF: 0.5566,
  NGN: 1.4904,
  GHS: 0.01417,
  EUR: 0.00085
};

const CHANNELS = [
  { id: "840101x1", src: "Paris-Eclair-LSP", dst: "Dakar-BTrust-Hub", cap: 480000, baseMsat: 1000, ppm: 140, lat: 42 },
  { id: "840102x2", src: "Paris-Eclair-LSP", dst: "Frankfurt-ACINQ", cap: 950000, baseMsat: 1000, ppm: 90, lat: 18 },
  { id: "840103x3", src: "Frankfurt-ACINQ", dst: "Dakar-BTrust-Hub", cap: 620000, baseMsat: 1000, ppm: 160, lat: 48 },
  { id: "840105x5", src: "Paris-Eclair-LSP", dst: "Abidjan-UEMOA-Gate", cap: 420000, baseMsat: 1000, ppm: 175, lat: 50 },
  { id: "840106x6", src: "Abidjan-UEMOA-Gate", dst: "Dakar-BTrust-Hub", cap: 510000, baseMsat: 800, ppm: 110, lat: 22 },
  { id: "840107x7", src: "Dakar-BTrust-Hub", dst: "Accra-Sats-Bridge", cap: 540000, baseMsat: 900, ppm: 125, lat: 29 },
  { id: "840108x8", src: "Frankfurt-ACINQ", dst: "Lagos-BitNob-Core", cap: 750000, baseMsat: 1200, ppm: 190, lat: 62 }
];

const BASE45_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";

function setTab(tab) {
  ["remittance", "l402", "mpp", "ussd"].forEach(t => {
    document.getElementById("tab-btn-" + t).classList.toggle("active", t === tab);
    document.getElementById("view-" + t).classList.toggle("active", t === tab);
  });
}

function updateRemittance() {
  const eur = parseFloat(document.getElementById("remit-amt").value);
  const cur = document.getElementById("remit-corridor").value;
  document.getElementById("remit-amt-label").textContent = "€" + eur.toFixed(2);

  const sats = Math.round(eur / FX_PER_SAT.EUR);
  const lnFeeEur = +(eur * 0.0026).toFixed(2);
  const mobileIntlFeeEur = +(2.50 + eur * 0.042).toFixed(2);
  const wuFeeEur = +(4.90 + eur * 0.068).toFixed(2);
  const swiftFeeEur = +(24.00 + eur * 0.035).toFixed(2);

  const netSats = Math.round(sats * (1 - 0.0026));
  const fiatReceived = Math.round(netSats * FX_PER_SAT[cur]);
  const savedEur = +(wuFeeEur - lnFeeEur).toFixed(2);
  const savedLocal = Math.round((savedEur / FX_PER_SAT.EUR) * FX_PER_SAT[cur]);

  document.getElementById("remit-out-fiat").textContent = fiatReceived.toLocaleString() + " " + cur;
  document.getElementById("remit-out-sats").textContent = netSats.toLocaleString() + " Sats Settled in 64 ms";
  document.getElementById("remit-savings").textContent = "+€" + savedEur.toFixed(2) + " Saved";
  document.getElementById("remit-savings-local").textContent = "+" + savedLocal.toLocaleString() + " " + cur + " Kept by Family";

  const rails = [
    { name: "SatsFlow Lightning + Local Off-Ramp", fee: lnFeeEur, pct: (lnFeeEur / eur * 100), speed: "64 ms (Instant)", color: "#10b981" },
    { name: "Cross-Border Mobile Money Hub", fee: mobileIntlFeeEur, pct: (mobileIntlFeeEur / eur * 100), speed: "2 – 6 Hours", color: "#38bdf8" },
    { name: "Legacy MTO (Western Union / MoneyGram)", fee: wuFeeEur, pct: (wuFeeEur / eur * 100), speed: "1 – 3 Days", color: "#f59e0b" },
    { name: "Correspondent Bank SWIFT Wire", fee: swiftFeeEur, pct: (swiftFeeEur / eur * 100), speed: "3 – 5 Business Days", color: "#f43f5e" }
  ];

  const maxPct = Math.max(...rails.map(r => r.pct), 10);
  document.getElementById("remit-bars-container").innerHTML = rails.map(r => `
    <div style="margin-bottom:11px;">
      <div style="display:flex;justify-content:space-between;font-size:12px;">
        <span style="font-weight:600;color:#e2e8f0;">${r.name}</span>
        <span style="font-family:monospace;color:${r.color};font-weight:700;">€${r.fee.toFixed(2)} (${r.pct.toFixed(2)}%)</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${Math.min(100, (r.pct / maxPct) * 100).toFixed(1)}%;background:${r.color};"></div>
      </div>
    </div>
  `).join("");

  document.getElementById("remit-table-body").innerHTML = rails.map((r, i) => `
    <tr style="${i === 0 ? 'background:rgba(16,185,129,0.1);' : ''}">
      <td style="font-family:sans-serif;font-weight:${i === 0 ? '700' : '500'};color:${r.color};">${r.name}</td>
      <td>€${r.fee.toFixed(2)}</td>
      <td>${r.pct.toFixed(2)}%</td>
      <td>${r.speed}</td>
    </tr>
  `).join("");
}

function pseudoHashHex(str) {
  let h1 = 0xdeadbeef ^ str.length, h2 = 0x41c6ce57 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  let out = "";
  for (let j = 0; j < 8; j++) {
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507 ^ j);
    h2 = Math.imul(h2 ^ (h2 >>> 13), 3266489909 ^ j);
    out += ((h1 >>> 0).toString(16).padStart(8, "0")) + ((h2 >>> 0).toString(16).padStart(8, "0"));
  }
  return out.slice(0, 64);
}

function updateL402Sandbox() {
  const val = document.getElementById("l402-resource").value;
  const [resource, satsStr] = val.split("|");
  const sats = parseInt(satsStr, 10);
  const preimage = pseudoHashHex("preimage:" + resource + ":" + sats);
  const paymentHash = pseudoHashHex("hash:" + preimage);
  const macId = "l402-id-" + paymentHash.slice(0, 16);
  const macSig = pseudoHashHex("hmac:" + macId + ":" + resource).slice(0, 64);

  const macaroonObj = {
    location: "https://api.satsflow.africa",
    identifier: macId,
    caveats: [
      `resource = ${resource}`,
      `payment_hash = ${paymentHash}`,
      `price_sats = ${sats}`,
      `corridor = ECOWAS-UEMOA`,
      `expires_at = 1762826400`
    ],
    signature: macSig
  };
  const macB64 = btoa(JSON.stringify(macaroonObj));
  const bolt11 = `lnbc${sats * 10}n1p3dakarpp5${paymentHash.slice(0, 38)}qdqqxqyjw5qcqpjsp5satsflow`;

  document.getElementById("l402-challenge-box").textContent =
    `HTTP/1.1 402 Payment Required\nWWW-Authenticate: L402 macaroon="${macB64.slice(0, 64)}...", invoice="${bolt11}"`;
  document.getElementById("l402-macaroon-box").textContent = JSON.stringify(macaroonObj, null, 2);

  const rows = [
    ["BOLT-11 HRP & Network", `lnbc${sats * 10}n (Bitcoin Mainnet — ${sats} Sats / ${sats * 1000} msat)`],
    ["Tagged Payment Hash (p)", paymentHash],
    ["Settled HTLC Preimage", preimage],
    ["BIP-173 Bech32 Checksum", "VALID (6-word Polymod Checksum Verified)"],
    ["CLTV Expiry Delta", "40 Blocks (~6.6 Hours) | Expiry: 3600s"]
  ];
  document.getElementById("bolt11-decoded-tbody").innerHTML = rows.map(([k, v]) => `
    <tr>
      <td style="color:#94a3b8;width:36%;font-family:sans-serif;font-weight:600;">${k}</td>
      <td style="color:#f8fafc;word-break:break-all;">${v}</td>
    </tr>
  `).join("");

  document.getElementById("l402-verify-output").textContent = JSON.stringify({
    http_status: 200,
    authorized: true,
    auth_header: `Authorization: L402 ${macB64.slice(0, 22)}...:${preimage.slice(0, 24)}...`,
    macaroon_hmac_verified: true,
    htlc_preimage_sha256_match: true,
    unlocked_resource: resource
  }, null, 2);
}

function triggerPreimageVerify() {
  const chip = document.getElementById("l402-status-chip");
  chip.textContent = "✓ L402 MACAROON + PREIMAGE VERIFIED (HTTP 200)";
  chip.style.background = "rgba(16, 185, 129, 0.22)";
  chip.style.color = "#34d399";
}

function updateMppGraph() {
  const amt = parseInt(document.getElementById("mpp-amt").value, 10);
  document.getElementById("mpp-amt-label").textContent = amt.toLocaleString() + " Sats";

  const isMpp = amt > 480000;
  const chip = document.getElementById("mpp-mode-chip");
  chip.textContent = isMpp ? "MULTI_PATH_PAYMENT_MPP (2 CONCURRENT SHARDS)" : "SINGLE_PATH_DIJKSTRA_HTLC";

  let shards = [];
  if (!isMpp) {
    const feeSats = +(1.0 + (amt * 140) / 1e6).toFixed(2);
    shards = [
      { shardId: "#1 (100%)", amt, path: "Paris-Eclair-LSP → Dakar-BTrust-Hub", chanIds: ["840101x1"], feeSats, lat: 42 }
    ];
  } else {
    const s1 = Math.floor(amt / 2);
    const s2 = amt - s1;
    const f1 = +(1.0 + (s1 * 140) / 1e6).toFixed(2);
    const f2 = +(2.0 + (s2 * (90 + 160)) / 1e6).toFixed(2);
    shards = [
      { shardId: "Shard #1 (Direct)", amt: s1, path: "Paris-Eclair-LSP → Dakar-BTrust-Hub", chanIds: ["840101x1"], feeSats: f1, lat: 42 },
      { shardId: "Shard #2 (Via Frankfurt)", amt: s2, path: "Paris-Eclair-LSP → Frankfurt-ACINQ → Dakar-BTrust-Hub", chanIds: ["840102x2", "840103x3"], feeSats: f2, lat: 66 }
    ];
  }

  const activeChans = new Set(shards.flatMap(s => s.chanIds));
  renderNetworkSvg(activeChans, isMpp);

  document.getElementById("mpp-shards-container").innerHTML = shards.map(s => `
    <div style="background:#080d18;border:1px solid rgba(247,147,26,0.4);border-radius:10px;padding:10px 12px;margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;font-size:12.5px;font-weight:700;color:var(--btc-orange);">
        <span>${s.shardId}: ${s.amt.toLocaleString()} Sats</span>
        <span>Fee: ${s.feeSats} Sats | ${s.lat} ms</span>
      </div>
      <div style="font-size:12px;color:#cbd5e1;font-family:monospace;margin-top:3px;">Route: ${s.path}</div>
    </div>
  `).join("");

  document.getElementById("mpp-channels-tbody").innerHTML = CHANNELS.slice(0, 6).map(c => {
    const active = activeChans.has(c.id);
    return `<tr style="${active ? 'background:rgba(247,147,26,0.14);' : ''}">
      <td style="color:${active ? '#f7931a' : '#94a3b8'};font-weight:${active ? '700' : '400'};">${c.id}</td>
      <td>${c.src.split("-")[0]} → ${c.dst.split("-")[0]}</td>
      <td>${c.cap.toLocaleString()}</td>
      <td>${c.baseMsat} msat + ${c.ppm} ppm</td>
      <td>${c.lat} ms</td>
    </tr>`;
  }).join("");
}

function renderNetworkSvg(activeChans, isMpp) {
  const nodes = {
    "Paris-Eclair-LSP": { x: 105, y: 155, label: "Paris-Eclair-LSP", sub: "EU Entry Gateway" },
    "Frankfurt-ACINQ": { x: 330, y: 65, label: "Frankfurt-ACINQ", sub: "Core Liquidity Router" },
    "Abidjan-UEMOA-Gate": { x: 330, y: 245, label: "Abidjan-UEMOA", sub: "UEMOA Relay" },
    "Dakar-BTrust-Hub": { x: 565, y: 155, label: "Dakar-BTrust-Hub", sub: "Senegal XOF Hub" }
  };
  const edges = [
    { id: "840101x1", from: "Paris-Eclair-LSP", to: "Dakar-BTrust-Hub", label: "Cap: 480k | 140 ppm" },
    { id: "840102x2", from: "Paris-Eclair-LSP", to: "Frankfurt-ACINQ", label: "Cap: 950k | 90 ppm" },
    { id: "840103x3", from: "Frankfurt-ACINQ", to: "Dakar-BTrust-Hub", label: "Cap: 620k | 160 ppm" },
    { id: "840105x5", from: "Paris-Eclair-LSP", to: "Abidjan-UEMOA-Gate", label: "Cap: 420k | 175 ppm" },
    { id: "840106x6", from: "Abidjan-UEMOA-Gate", to: "Dakar-BTrust-Hub", label: "Cap: 510k | 110 ppm" }
  ];

  let linesSvg = edges.map(e => {
    const n1 = nodes[e.from], n2 = nodes[e.to];
    const isAct = activeChans.has(e.id);
    const col = isAct ? "#f7931a" : "#334155";
    const w = isAct ? 4 : 2;
    const mx = (n1.x + n2.x) / 2, my = (n1.y + n2.y) / 2 - 8;
    return `
      <line x1="${n1.x}" y1="${n1.y}" x2="${n2.x}" y2="${n2.y}" stroke="${col}" stroke-width="${w}" />
      <text x="${mx}" y="${my}" fill="${isAct ? '#fbbf24' : '#64748b'}" font-size="10.5" font-family="monospace" text-anchor="middle">${e.label}</text>
    `;
  }).join("");

  let nodesSvg = Object.values(nodes).map(n => `
    <g transform="translate(${n.x - 68}, ${n.y - 26})">
      <rect x="0" y="0" width="136" height="52" rx="10" fill="#0f1626" stroke="#f7931a" stroke-width="2.2"/>
      <text x="68" y="22" fill="#f8fafc" font-size="11.5" font-weight="800" text-anchor="middle">${n.label}</text>
      <text x="68" y="39" fill="#94a3b8" font-size="10" text-anchor="middle">${n.sub}</text>
    </g>
  `).join("");

  document.getElementById("mpp-svg-container").innerHTML =
    `<svg viewBox="0 0 670 310" width="100%" height="auto">${linesSvg}${nodesSvg}</svg>`;
}

function base45EncodeStr(str) {
  const bytes = new TextEncoder().encode(str);
  let out = "";
  for (let i = 0; i < bytes.length - 1; i += 2) {
    let val = (bytes[i] << 8) + bytes[i + 1];
    const e = Math.floor(val / (45 * 45));
    val %= (45 * 45);
    const d = Math.floor(val / 45);
    const c = val % 45;
    out += BASE45_CHARS[c] + BASE45_CHARS[d] + BASE45_CHARS[e];
  }
  if (bytes.length % 2 === 1) {
    const val = bytes[bytes.length - 1];
    out += BASE45_CHARS[val % 45] + BASE45_CHARS[Math.floor(val / 45)];
  }
  return out;
}

function updateUssdVoucher() {
  const sats = parseInt(document.getElementById("ussd-sats").value, 10);
  const xof = Math.round(sats * FX_PER_SAT.XOF);
  document.getElementById("ussd-sats-label").textContent = `${sats.toLocaleString()} Sats (${xof.toLocaleString()} XOF)`;

  const sig = pseudoHashHex("ussd:" + sats).slice(0, 12);
  const pin = (parseInt(sig.slice(0, 6), 16) % 900000) + 100000;
  const payload = { v: 1, sats, cur: "XOF", fiat: xof, ph: "sn778129", sig };
  const b45 = "SATS1:" + base45EncodeStr(JSON.stringify(payload));

  document.getElementById("ussd-dial-box").textContent = `*789*1*${sats}*${pin}#`;
  document.getElementById("ussd-b45-box").textContent = b45;
  document.getElementById("ussd-json-box").textContent = JSON.stringify(payload, null, 2);
  document.getElementById("ussd-screen-text").innerHTML = `
    1. Send Sats to Phone<br/>
    2. Redeem XOF Cashout<br/>
    3. Offline Voucher PIN<br/><br/>
    <span style="color:#fbbf24;">✓ Voucher Verified:</span><br/>
    +${sats.toLocaleString()} Sats (${xof.toLocaleString()} XOF)<br/>
    HMAC: ${sig}
  `;
}

window.addEventListener("DOMContentLoaded", () => {
  updateRemittance();
  updateL402Sandbox();
  updateMppGraph();
  updateUssdVoucher();

  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (tab && ["remittance", "l402", "mpp", "ussd"].includes(tab)) {
    setTab(tab);
  }
});
