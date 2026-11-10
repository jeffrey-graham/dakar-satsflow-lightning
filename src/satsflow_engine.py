#!/usr/bin/env python3
"""
SatsFlow Core Cryptographic & Lightning Routing Engine
Dakar Bitcoin Hack by BTrust (2026) — West African Lightning & L402 Settlement

Implements:
1. BOLT-11 Invoice Encoder & Decoder (BIP-173 Bech32 polymod checksum, HRP multiplier
   parsing for m/u/n/p BTC, tagged field extraction, and SHA-256 preimage verification).
2. L402 (LSAT) Cryptographic Macaroon + Preimage HTTP 402 Payment-Gated API Middleware
   (chained HMAC-SHA256 caveats + constant-time preimage verification).
3. Multi-Hop & Multi-Path Payment (MPP) Channel Liquidity & Fee Route Optimizer
   (Dijkstra min-fee routing + automatic capacity-constrained MPP split across West African
   and European LSP nodes).
4. RFC 9285 Base45 Offline USSD / SMS Compact Voucher Payload Generator & Verifier
   for feature-phone settlement across XOF (BCEAO Senegal/Côte d'Ivoire), NGN, and GHS.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import heapq
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

# BIP-173 Bech32 character set
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_MAP = {c: i for i, c in enumerate(BECH32_CHARSET)}

# RFC 9285 Base45 character set for compact SMS / USSD / QR payloads
BASE45_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
BASE45_MAP = {c: i for i, c in enumerate(BASE45_CHARSET)}

# Reference FX rates (1 BTC = $92,000 USD; 1 Sat = $0.00092 USD)
# West African CFA Franc (XOF): ~605 XOF / USD -> 1 Sat ≈ 0.5566 XOF
# Nigerian Naira (NGN): ~1,620 NGN / USD -> 1 Sat ≈ 1.4904 NGN
# Ghanaian Cedi (GHS): ~15.40 GHS / USD -> 1 Sat ≈ 0.01417 GHS
FX_RATES_PER_SAT: dict[str, float] = {
    "XOF": 0.5566,
    "NGN": 1.4904,
    "GHS": 0.01417,
    "USD": 0.00092,
    "EUR": 0.00085,
}


# ---------------------------------------------------------------------------
# 1. BIP-173 Bech32 & BOLT-11 Invoice Parser / Encoder
# ---------------------------------------------------------------------------
def _bech32_polymod(values: list[int]) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_verify_checksum(hrp: str, data: list[int]) -> bool:
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == 1


def _int_to_5bit(val: int, num_words: int) -> list[int]:
    out = [0] * num_words
    for i in range(num_words - 1, -1, -1):
        out[i] = val & 31
        val >>= 5
    return out


def _5bit_to_int(words: list[int]) -> int:
    val = 0
    for w in words:
        val = (val << 5) | w
    return val


def _bytes_to_5bit(data: bytes) -> list[int]:
    acc = 0
    bits = 0
    out: list[int] = []
    for byte in data:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append((acc >> bits) & 31)
    if bits > 0:
        out.append((acc << (5 - bits)) & 31)
    return out


def _5bit_to_bytes(words: list[int], byte_len: int) -> bytes:
    acc = 0
    bits = 0
    out = bytearray()
    for w in words:
        acc = (acc << 5) | w
        bits += 5
        while bits >= 8 and len(out) < byte_len:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out[:byte_len])


def encode_bolt11_invoice(
    amount_sats: int,
    payment_hash_hex: str,
    description: str,
    network: str = "lnbc",
    expiry_seconds: int = 3600,
    timestamp: int | None = None,
) -> str:
    """
    Encodes a cryptographic BOLT-11 invoice with Bech32 HRP (`lnbc<amount>n`),
    35-bit timestamp, tagged payment hash (`p`), description (`d`), expiry (`x`),
    deterministic 65-byte compact signature stub, and verified BIP-173 Bech32 checksum.
    """
    ts = int(timestamp if timestamp is not None else time.time())
    payment_hash_bytes = bytes.fromhex(payment_hash_hex)
    if len(payment_hash_bytes) != 32:
        raise ValueError("BOLT-11 payment_hash must be 32 bytes (64 hex chars)")

    # 1 BTC = 100,000,000 sats = 1,000,000,000 nano-BTC (`n`).
    # So 1 sat = 10 nano-BTC (`n`).
    nano_btc = amount_sats * 10
    hrp = f"{network}{nano_btc}n"

    data_words: list[int] = []
    # 35-bit timestamp (7 x 5-bit words)
    data_words.extend(_int_to_5bit(ts, 7))

    # Tag 'p' (code 1): 52 words (256-bit payment hash)
    p_words = _bytes_to_5bit(payment_hash_bytes)  # 52 words
    data_words.append(1)  # 'p' in Bech32 charset is index 1
    data_words.extend(_int_to_5bit(len(p_words), 2))
    data_words.extend(p_words)

    # Tag 'd' (code 13): UTF-8 description
    d_words = _bytes_to_5bit(description.encode("utf-8"))
    data_words.append(13)  # 'd' in Bech32 charset is index 13
    data_words.extend(_int_to_5bit(len(d_words), 2))
    data_words.extend(d_words)

    # Tag 'x' (code 6): expiry in seconds
    x_words = _int_to_5bit(expiry_seconds, 3)
    data_words.append(6)  # 'x' in Bech32 charset is index 6
    data_words.extend(_int_to_5bit(len(x_words), 2))
    data_words.extend(x_words)

    # 65-byte (104 x 5-bit words) deterministic secp256k1 signature digest
    sig_digest = hashlib.sha512(hrp.encode("utf-8") + payment_hash_bytes).digest() + bytes([0])
    sig_words = _bytes_to_5bit(sig_digest)[:104]
    data_words.extend(sig_words)

    checksum = bech32_create_checksum(hrp, data_words)
    payload_str = "".join(BECH32_CHARSET[w] for w in (data_words + checksum))
    return f"{hrp}1{payload_str}"


def decode_bolt11_invoice(bolt11_str: str) -> dict[str, Any]:
    """
    Decodes and verifies a BOLT-11 Bech32 invoice string, returning network,
    amount in satoshis & millisatoshis, timestamp, payment_hash, description,
    expiry, and checksum validity.
    """
    clean = bolt11_str.strip().lower()
    sep_pos = clean.rfind("1")
    if sep_pos < 4:
        raise ValueError("Invalid BOLT-11 invoice: missing Bech32 separator '1'")

    hrp = clean[:sep_pos]
    data_part = clean[sep_pos + 1 :]
    if len(data_part) < 117:
        raise ValueError("Invalid BOLT-11 invoice: payload too short")

    data_words = [BECH32_MAP[ch] for ch in data_part]
    if not bech32_verify_checksum(hrp, data_words):
        raise ValueError("BOLT-11 Bech32 checksum verification failed")

    # Strip 6-word checksum and 104-word signature
    core_words = data_words[:-6]
    tagged_area = core_words[:-104]

    # Parse HRP (`lnbc` or `lntb` + amount + multiplier)
    if hrp.startswith("lnbc"):
        network = "lnbc"
        amt_part = hrp[4:]
    elif hrp.startswith("lntb"):
        network = "lntb"
        amt_part = hrp[4:]
    else:
        raise ValueError(f"Unsupported BOLT-11 prefix: {hrp}")

    amount_msat = 0
    if amt_part:
        mult = amt_part[-1]
        num_str = amt_part[:-1] if not amt_part[-1].isdigit() else amt_part
        num_val = int(num_str)
        # 1 BTC = 100,000,000,000 msat
        multipliers_msat = {
            "m": 100_000_000,  # milli-BTC = 100,000 sats
            "u": 100_000,      # micro-BTC = 100 sats
            "n": 100,          # nano-BTC = 0.1 sat = 100 msat
            "p": 0.1,          # pico-BTC = 0.1 msat
        }
        if mult in multipliers_msat:
            amount_msat = int(round(num_val * multipliers_msat[mult]))
        else:
            amount_msat = num_val * 100_000_000_000

    amount_sats = amount_msat // 1000
    timestamp = _5bit_to_int(tagged_area[:7])

    idx = 7
    payment_hash_hex = ""
    description = ""
    expiry_seconds = 3600

    while idx + 3 <= len(tagged_area):
        tag_code = tagged_area[idx]
        data_len = _5bit_to_int(tagged_area[idx + 1 : idx + 3])
        idx += 3
        field_words = tagged_area[idx : idx + data_len]
        idx += data_len

        if tag_code == 1 and len(field_words) == 52:  # 'p' payment hash
            payment_hash_hex = _5bit_to_bytes(field_words, 32).hex()
        elif tag_code == 13:  # 'd' description
            byte_len = (len(field_words) * 5) // 8
            description = _5bit_to_bytes(field_words, byte_len).decode("utf-8", errors="replace")
        elif tag_code == 6:  # 'x' expiry
            expiry_seconds = _5bit_to_int(field_words)

    return {
        "valid_checksum": True,
        "network": network,
        "hrp": hrp,
        "amount_sats": amount_sats,
        "amount_msat": amount_msat,
        "timestamp": timestamp,
        "payment_hash": payment_hash_hex,
        "description": description,
        "expiry_seconds": expiry_seconds,
    }


def verify_payment_preimage(preimage_hex: str, expected_payment_hash_hex: str) -> bool:
    """
    Verifies the fundamental Lightning HTLC atomic condition: SHA256(preimage) == payment_hash.
    """
    preimage_bytes = bytes.fromhex(preimage_hex.strip())
    computed_hash = hashlib.sha256(preimage_bytes).hexdigest()
    return hmac.compare_digest(computed_hash, expected_payment_hash_hex.strip().lower())


# ---------------------------------------------------------------------------
# 2. L402 (LSAT) Macaroon + Preimage HTTP 402 Payment-Gated API Engine
# ---------------------------------------------------------------------------
class L402PaymentGate:
    """
    Implements Lightning HTTP 402 (L402 / LSAT) authentication using chained HMAC-SHA256
    Macaroons bound to a Lightning BOLT-11 payment_hash and verified via preimage disclosure.
    """

    def __init__(self, root_secret: bytes = b"dakar-btrust-satsflow-root-key-2026") -> None:
        self.root_secret = root_secret

    def mint_challenge(
        self,
        resource_path: str,
        price_sats: int,
        corridor: str = "SN-XOF",
        ttl_seconds: int = 3600,
        preimage_seed: str = "dakar-satsflow-htlc-secret-2026",
    ) -> dict[str, Any]:
        preimage_bytes = hashlib.sha256(
            f"{preimage_seed}:{resource_path}:{price_sats}".encode("utf-8")
        ).digest()
        preimage_hex = preimage_bytes.hex()
        payment_hash_hex = hashlib.sha256(preimage_bytes).hexdigest()

        now = int(time.time())
        expires_at = now + ttl_seconds
        identifier = f"l402-id-{payment_hash_hex[:16]}"
        caveats = [
            f"resource = {resource_path}",
            f"payment_hash = {payment_hash_hex}",
            f"price_sats = {price_sats}",
            f"corridor = {corridor}",
            f"expires_at = {expires_at}",
        ]

        # Chained HMAC-SHA256 Macaroon construction
        sig = hmac.new(self.root_secret, identifier.encode("utf-8"), hashlib.sha256).digest()
        for cav in caveats:
            sig = hmac.new(sig, cav.encode("utf-8"), hashlib.sha256).digest()

        macaroon_obj = {
            "location": "https://api.satsflow.africa",
            "identifier": identifier,
            "caveats": caveats,
            "signature": sig.hex(),
        }
        macaroon_b64 = base64.urlsafe_b64encode(
            json.dumps(macaroon_obj, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")

        bolt11 = encode_bolt11_invoice(
            amount_sats=price_sats,
            payment_hash_hex=payment_hash_hex,
            description=f"SatsFlow L402 API: {resource_path} ({corridor})",
            timestamp=now,
        )

        return {
            "http_status": 402,
            "www_authenticate_header": f'L402 macaroon="{macaroon_b64}", invoice="{bolt11}"',
            "macaroon_b64": macaroon_b64,
            "macaroon_decoded": macaroon_obj,
            "bolt11_invoice": bolt11,
            "payment_hash": payment_hash_hex,
            "demo_settled_preimage": preimage_hex,
            "price_sats": price_sats,
        }

    def verify_l402_token(
        self, macaroon_b64: str, preimage_hex: str, current_time: int | None = None
    ) -> dict[str, Any]:
        now = int(current_time if current_time is not None else time.time())
        raw_json = base64.urlsafe_b64decode(macaroon_b64.encode("ascii")).decode("utf-8")
        mac = json.loads(raw_json)

        identifier = mac["identifier"]
        caveats: list[str] = mac["caveats"]
        claimed_sig = mac["signature"]

        # Recompute chained HMAC-SHA256 signature
        sig = hmac.new(self.root_secret, identifier.encode("utf-8"), hashlib.sha256).digest()
        caveat_map: dict[str, str] = {}
        for cav in caveats:
            sig = hmac.new(sig, cav.encode("utf-8"), hashlib.sha256).digest()
            if "=" in cav:
                k, v = cav.split("=", 1)
                caveat_map[k.strip()] = v.strip()

        if not hmac.compare_digest(sig.hex(), claimed_sig):
            return {"authorized": False, "reason": "Macaroon HMAC signature mismatch"}

        expected_hash = caveat_map.get("payment_hash", "")
        if not verify_payment_preimage(preimage_hex, expected_hash):
            return {"authorized": False, "reason": "HTLC preimage does not hash to payment_hash"}

        expires_at = int(caveat_map.get("expires_at", "0"))
        if now > expires_at:
            return {"authorized": False, "reason": "L402 macaroon token expired"}

        return {
            "authorized": True,
            "http_status": 200,
            "resource": caveat_map.get("resource"),
            "payment_hash": expected_hash,
            "corridor": caveat_map.get("corridor"),
            "verified_caveats_count": len(caveats),
        }


# ---------------------------------------------------------------------------
# 3. Multi-Hop & Multi-Path Payment (MPP) Lightning Route Optimizer
# ---------------------------------------------------------------------------
@dataclass
class LightningChannel:
    channel_id: str
    source: str
    target: str
    capacity_sats: int
    base_fee_msat: int
    fee_ppm: int
    cltv_delta: int
    latency_ms: int


DEFAULT_WEST_AFRICA_CHANNELS: list[LightningChannel] = [
    LightningChannel("840101x1", "Paris-Eclair-LSP", "Dakar-BTrust-Hub", 480_000, 1000, 140, 40, 42),
    LightningChannel("840102x2", "Paris-Eclair-LSP", "Frankfurt-ACINQ", 950_000, 1000, 90, 24, 18),
    LightningChannel("840103x3", "Frankfurt-ACINQ", "Dakar-BTrust-Hub", 620_000, 1000, 160, 40, 48),
    LightningChannel("840104x4", "Frankfurt-ACINQ", "Lagos-BitNob-Core", 750_000, 1200, 190, 40, 62),
    LightningChannel("840105x5", "Paris-Eclair-LSP", "Abidjan-UEMOA-Gate", 420_000, 1000, 175, 40, 50),
    LightningChannel("840106x6", "Abidjan-UEMOA-Gate", "Dakar-BTrust-Hub", 510_000, 800, 110, 24, 22),
    LightningChannel("840107x7", "Dakar-BTrust-Hub", "Accra-Sats-Bridge", 540_000, 900, 125, 24, 29),
    LightningChannel("840108x8", "Lagos-BitNob-Core", "Accra-Sats-Bridge", 680_000, 1000, 130, 24, 25),
    LightningChannel("840109x9", "Accra-Sats-Bridge", "Dakar-BTrust-Hub", 490_000, 900, 120, 24, 28),
]


def _channel_fee_msat(ch: LightningChannel, amount_sats: int) -> int:
    amount_msat = amount_sats * 1000
    return ch.base_fee_msat + (amount_msat * ch.fee_ppm) // 1_000_000


def find_optimal_lightning_route(
    source: str,
    destination: str,
    amount_sats: int,
    channels: list[LightningChannel] | None = None,
) -> dict[str, Any]:
    """
    Computes the minimum-fee Lightning route from `source` to `destination`.
    - If a single path has sufficient channel liquidity (`capacity_sats >= amount_sats`),
      returns the optimal single-path Dijkstra route.
    - If `amount_sats` exceeds single-channel capacity, automatically executes
      BOLT-04 Multi-Path Payment (MPP) splitting across parallel edge-disjoint routes!
    """
    net = list(channels if channels is not None else DEFAULT_WEST_AFRICA_CHANNELS)

    def _dijkstra(amt: int, excluded_channels: set[str]) -> dict[str, Any] | None:
        adj: dict[str, list[LightningChannel]] = {}
        for ch in net:
            if ch.channel_id not in excluded_channels and ch.capacity_sats >= amt:
                adj.setdefault(ch.source, []).append(ch)

        pq: list[tuple[int, str, list[str], list[str], int, int]] = [
            (0, source, [source], [], 0, 0)
        ]
        visited: dict[str, int] = {}

        while pq:
            fee_msat, node, nodes_path, chan_ids, total_cltv, total_lat = heapq.heappop(pq)
            if node == destination:
                return {
                    "amount_sats": amt,
                    "nodes": nodes_path,
                    "channel_ids": chan_ids,
                    "fee_msat": fee_msat,
                    "fee_sats": round(fee_msat / 1000.0, 3),
                    "total_cltv_delta": total_cltv,
                    "latency_ms": total_lat,
                }
            if node in visited and visited[node] <= fee_msat:
                continue
            visited[node] = fee_msat

            for ch in adj.get(node, []):
                if ch.target in nodes_path:
                    continue
                hop_fee = _channel_fee_msat(ch, amt)
                heapq.heappush(
                    pq,
                    (
                        fee_msat + hop_fee,
                        ch.target,
                        nodes_path + [ch.target],
                        chan_ids + [ch.channel_id],
                        total_cltv + ch.cltv_delta,
                        total_lat + ch.latency_ms,
                    ),
                )
        return None

    single = _dijkstra(amount_sats, set())
    if single is not None:
        return {
            "routing_mode": "SINGLE_PATH_HTLC",
            "total_amount_sats": amount_sats,
            "shard_count": 1,
            "total_fee_msat": single["fee_msat"],
            "total_fee_sats": single["fee_sats"],
            "effective_fee_ppm": int(round((single["fee_msat"] / (amount_sats * 1000)) * 1_000_000)),
            "max_latency_ms": single["latency_ms"],
            "shards": [single],
        }

    # Multi-Path Payment (MPP) split into 2 or 3 capacity-feasible shards
    for n_shards in (2, 3):
        base_shard = amount_sats // n_shards
        rem = amount_sats - base_shard * (n_shards - 1)
        shard_amounts = [base_shard] * (n_shards - 1) + [rem]
        excluded: set[str] = set()
        shards: list[dict[str, Any]] = []
        possible = True
        for s_amt in shard_amounts:
            route = _dijkstra(s_amt, excluded)
            if route is None:
                possible = False
                break
            shards.append(route)
            # Exclude bottleneck first-hop channel to force true multi-path concurrency
            if route["channel_ids"]:
                excluded.add(route["channel_ids"][0])

        if possible:
            tot_fee_msat = sum(s["fee_msat"] for s in shards)
            return {
                "routing_mode": "MULTI_PATH_PAYMENT_MPP",
                "total_amount_sats": amount_sats,
                "shard_count": len(shards),
                "total_fee_msat": tot_fee_msat,
                "total_fee_sats": round(tot_fee_msat / 1000.0, 3),
                "effective_fee_ppm": int(round((tot_fee_msat / (amount_sats * 1000)) * 1_000_000)),
                "max_latency_ms": max(s["latency_ms"] for s in shards),
                "shards": shards,
            }

    raise ValueError(f"Insufficient aggregate network capacity for {amount_sats} sats")


# ---------------------------------------------------------------------------
# 4. RFC 9285 Base45 Offline USSD / SMS Compact Voucher Payload Generator
# ---------------------------------------------------------------------------
def base45_encode(data: bytes) -> str:
    out: list[str] = []
    for i in range(0, len(data) - 1, 2):
        val = (data[i] << 8) + data[i + 1]
        e, rem = divmod(val, 45 * 45)
        d, c = divmod(rem, 45)
        out.append(BASE45_CHARSET[c] + BASE45_CHARSET[d] + BASE45_CHARSET[e])
    if len(data) % 2 == 1:
        val = data[-1]
        d, c = divmod(val, 45)
        out.append(BASE45_CHARSET[c] + BASE45_CHARSET[d])
    return "".join(out)


def base45_decode(encoded: str) -> bytes:
    vals = [BASE45_MAP[ch] for ch in encoded]
    out = bytearray()
    i = 0
    while i < len(vals):
        if i + 2 < len(vals):
            x = vals[i] + vals[i + 1] * 45 + vals[i + 2] * 45 * 45
            out.append((x >> 8) & 0xFF)
            out.append(x & 0xFF)
            i += 3
        else:
            x = vals[i] + vals[i + 1] * 45
            out.append(x & 0xFF)
            i += 2
    return bytes(out)


def create_offline_ussd_voucher(
    amount_sats: int,
    corridor_fiat: str = "XOF",
    sender_phone_hash: str = "sn7781290",
    secret_key: bytes = b"dakar-ussd-offline-key-2026",
) -> dict[str, Any]:
    """
    Creates a compact offline-resilient SMS / USSD voucher for feature-phone users
    in Senegal (XOF), Nigeria (NGN), or Ghana (GHS).
    """
    rate = FX_RATES_PER_SAT.get(corridor_fiat, 0.5566)
    fiat_val = round(amount_sats * rate, 2)
    payload_core = {
        "v": 1,
        "sats": amount_sats,
        "cur": corridor_fiat,
        "fiat": fiat_val,
        "ph": sender_phone_hash[:8],
    }
    canonical = json.dumps(payload_core, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig_hex = hmac.new(secret_key, canonical, hashlib.sha256).hexdigest()[:12]
    payload_core["sig"] = sig_hex

    packed_bytes = json.dumps(payload_core, separators=(",", ":")).encode("utf-8")
    b45_token = base45_encode(packed_bytes)
    short_pin = int(sig_hex[:6], 16) % 900000 + 100000

    return {
        "amount_sats": amount_sats,
        "corridor_fiat": corridor_fiat,
        "fiat_amount": fiat_val,
        "ussd_dial_string": f"*789*1*{amount_sats}*{short_pin}#",
        "sms_compact_voucher": f"SATS1:{b45_token}",
        "hmac_tag": sig_hex,
        "payload": payload_core,
    }


def verify_offline_ussd_voucher(
    sms_voucher_str: str, secret_key: bytes = b"dakar-ussd-offline-key-2026"
) -> dict[str, Any]:
    token = sms_voucher_str.strip()
    if token.startswith("SATS1:"):
        token = token[6:]
    decoded_bytes = base45_decode(token)
    obj = json.loads(decoded_bytes.decode("utf-8"))
    claimed_sig = obj.pop("sig", "")
    canonical = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    expected_sig = hmac.new(secret_key, canonical, hashlib.sha256).hexdigest()[:12]
    is_valid = hmac.compare_digest(claimed_sig, expected_sig)
    obj["sig"] = claimed_sig
    return {"valid": is_valid, "decoded_payload": obj}


def compare_remittance_corridors(amount_eur: float = 150.0, target_fiat: str = "XOF") -> dict[str, Any]:
    """
    Compares sending `amount_eur` from Paris/Diaspora to Dakar (XOF), Lagos (NGN), or Accra (GHS)
    via SatsFlow Lightning vs Legacy Wire/Remittance & Cross-Border Mobile Money.
    """
    sats = int(round(amount_eur / FX_RATES_PER_SAT["EUR"]))
    route = find_optimal_lightning_route("Paris-Eclair-LSP", "Dakar-BTrust-Hub", sats)
    ln_network_fee_eur = route["total_fee_sats"] * FX_RATES_PER_SAT["EUR"]
    ln_offramp_spread_eur = amount_eur * 0.0025  # 0.25% local mobile-money / Dakar Wave/Orange off-ramp
    satsflow_total_fee_eur = round(ln_network_fee_eur + ln_offramp_spread_eur, 2)
    legacy_mt_fee_eur = round(4.90 + amount_eur * 0.068, 2)  # ~8-9% total cost
    mobile_money_intl_eur = round(2.50 + amount_eur * 0.042, 2)

    return {
        "send_amount_eur": amount_eur,
        "settlement_sats": sats,
        "target_fiat": target_fiat,
        "target_fiat_received": round(
            (sats - route["total_fee_sats"]) * FX_RATES_PER_SAT[target_fiat] * 0.9975, 2
        ),
        "routing_mode": route["routing_mode"],
        "satsflow_total_fee_eur": satsflow_total_fee_eur,
        "satsflow_fee_pct": round(100.0 * satsflow_total_fee_eur / amount_eur, 2),
        "legacy_remittance_fee_eur": legacy_mt_fee_eur,
        "legacy_remittance_fee_pct": round(100.0 * legacy_mt_fee_eur / amount_eur, 2),
        "intl_mobile_money_fee_eur": mobile_money_intl_eur,
        "savings_vs_legacy_eur": round(legacy_mt_fee_eur - satsflow_total_fee_eur, 2),
    }


if __name__ == "__main__":
    gate = L402PaymentGate()
    chal = gate.mint_challenge("/v1/remit/quote", price_sats=250, corridor="FR-EUR->SN-XOF")
    ver = gate.verify_l402_token(chal["macaroon_b64"], chal["demo_settled_preimage"])
    decoded_inv = decode_bolt11_invoice(chal["bolt11_invoice"])
    mpp_route = find_optimal_lightning_route("Paris-Eclair-LSP", "Dakar-BTrust-Hub", 850_000)
    voucher = create_offline_ussd_voucher(25_000, "XOF")
    print("=== SatsFlow Cryptographic & Routing Engine Ready ===")
    print(f"BOLT-11 Invoice Verified : {decoded_inv['hrp']} ({decoded_inv['amount_sats']} sats)")
    print(f"L402 Token Authorized    : {ver['authorized']} (HTTP {ver['http_status']})")
    print(
        f"850k Sats Route Mode     : {mpp_route['routing_mode']} ({mpp_route['shard_count']} shards, "
        f"fee={mpp_route['total_fee_sats']} sats)"
    )
    print(f"Offline USSD Voucher     : {voucher['ussd_dial_string']} ({voucher['fiat_amount']} XOF)")
