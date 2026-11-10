#!/usr/bin/env python3
"""
Unit & Integration Test Suite for SatsFlow (`src/satsflow_engine.py`).
Run with: python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import unittest

from src.satsflow_engine import (
    L402PaymentGate,
    compare_remittance_corridors,
    create_offline_ussd_voucher,
    decode_bolt11_invoice,
    encode_bolt11_invoice,
    find_optimal_lightning_route,
    verify_offline_ussd_voucher,
    verify_payment_preimage,
)


class TestSatsFlowEngine(unittest.TestCase):
    def test_bolt11_bech32_encode_decode_roundtrip_and_checksum(self) -> None:
        preimage = hashlib.sha256(b"dakar-btrust-test-preimage").digest()
        payment_hash = hashlib.sha256(preimage).hexdigest()
        invoice = encode_bolt11_invoice(
            amount_sats=42500,
            payment_hash_hex=payment_hash,
            description="Dakar XOF Settlement #101",
            network="lnbc",
            expiry_seconds=1800,
            timestamp=1762740000,
        )
        decoded = decode_bolt11_invoice(invoice)
        self.assertTrue(decoded["valid_checksum"])
        self.assertEqual(decoded["network"], "lnbc")
        self.assertEqual(decoded["amount_sats"], 42500)
        self.assertEqual(decoded["amount_msat"], 42500000)
        self.assertEqual(decoded["payment_hash"], payment_hash)
        self.assertEqual(decoded["description"], "Dakar XOF Settlement #101")
        self.assertEqual(decoded["expiry_seconds"], 1800)
        self.assertTrue(verify_payment_preimage(preimage.hex(), payment_hash))

        # Tampering with a single Bech32 character must fail checksum verification
        tampered = invoice[:-2] + ("p" if invoice[-2] != "p" else "q") + invoice[-1]
        with self.assertRaises(ValueError):
            decode_bolt11_invoice(tampered)

    def test_l402_macaroon_challenge_and_preimage_verification(self) -> None:
        gate = L402PaymentGate()
        chal = gate.mint_challenge("/v1/xof-payout", price_sats=500, corridor="SN-XOF")
        self.assertEqual(chal["http_status"], 402)
        self.assertIn("L402 macaroon=", chal["www_authenticate_header"])

        # Valid macaroon + matching HTLC preimage -> HTTP 200 Authorized
        res = gate.verify_l402_token(chal["macaroon_b64"], chal["demo_settled_preimage"])
        self.assertTrue(res["authorized"])
        self.assertEqual(res["http_status"], 200)
        self.assertEqual(res["resource"], "/v1/xof-payout")

        # Invalid preimage -> Rejected
        bad_preimage = "00" * 32
        res_bad = gate.verify_l402_token(chal["macaroon_b64"], bad_preimage)
        self.assertFalse(res_bad["authorized"])

    def test_single_path_and_mpp_multi_path_lightning_routing(self) -> None:
        # 150,000 sats fits inside a single channel (capacity 480,000 sats)
        single_route = find_optimal_lightning_route("Paris-Eclair-LSP", "Dakar-BTrust-Hub", 150_000)
        self.assertEqual(single_route["routing_mode"], "SINGLE_PATH_HTLC")
        self.assertEqual(single_route["shard_count"], 1)
        self.assertGreater(single_route["total_fee_msat"], 0)

        # 800,000 sats exceeds any single channel out of Paris-Eclair-LSP -> triggers MPP split
        mpp_route = find_optimal_lightning_route("Paris-Eclair-LSP", "Dakar-BTrust-Hub", 800_000)
        self.assertEqual(mpp_route["routing_mode"], "MULTI_PATH_PAYMENT_MPP")
        self.assertGreaterEqual(mpp_route["shard_count"], 2)
        self.assertEqual(
            sum(s["amount_sats"] for s in mpp_route["shards"]),
            800_000,
        )

    def test_base45_offline_ussd_voucher_roundtrip(self) -> None:
        voucher = create_offline_ussd_voucher(amount_sats=50_000, corridor_fiat="XOF")
        self.assertTrue(voucher["ussd_dial_string"].startswith("*789*1*50000*"))
        self.assertTrue(voucher["sms_compact_voucher"].startswith("SATS1:"))

        verified = verify_offline_ussd_voucher(voucher["sms_compact_voucher"])
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["decoded_payload"]["sats"], 50_000)
        self.assertEqual(verified["decoded_payload"]["cur"], "XOF")

    def test_remittance_corridor_savings(self) -> None:
        comp = compare_remittance_corridors(amount_eur=200.0, target_fiat="XOF")
        self.assertLess(comp["satsflow_fee_pct"], 0.5)
        self.assertGreater(comp["legacy_remittance_fee_pct"], 7.0)
        self.assertGreater(comp["savings_vs_legacy_eur"], 15.0)


if __name__ == "__main__":
    unittest.main()
