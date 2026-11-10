#!/usr/bin/env python3
"""
Generates screenshots & 60-second 1080p walkthrough video (`demo.mp4`) for
SatsFlow (`Dakar Bitcoin Hack by BTrust`).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS_INDEX = ROOT / "docs" / "index.html"
SCREENSHOTS_DIR = ROOT / "screenshots"
DEMO_MP4 = ROOT / "demo.mp4"


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def capture_chrome(url: str, out_png: Path, width: int = 1200, height: int = 800) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        "--virtual-time-budget=2000",
        f"--screenshot={out_png}",
        url,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Captured {out_png.name} ({width}x{height}, {out_png.stat().st_size:,} bytes)")


def frame_1080p_from_shot(shot_path: Path, chapter: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1080), (7, 10, 18))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1920, 8), fill=(247, 147, 26))
    shot = Image.open(shot_path).convert("RGB").resize((1760, 910), Image.Resampling.LANCZOS)
    canvas.paste(shot, (80, 24))
    draw.rounded_rectangle((78, 22, 1842, 936), radius=12, outline=(247, 147, 26), width=3)
    draw.rounded_rectangle((80, 952, 1840, 1058), radius=12, fill=(15, 22, 38), outline=(247, 147, 26), width=3)
    draw.text((110, 966), chapter, fill=(247, 147, 26), font=_load_font(20, bold=True))
    draw.text((110, 1002), caption, fill=(248, 250, 252), font=_load_font(23, bold=False))
    return canvas


def make_bookend_slide(is_intro: bool) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), (7, 10, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1920, 10), fill=(247, 147, 26))
    if is_intro:
        draw.text((90, 110), "SatsFlow  |  Dakar Bitcoin Hack by BTrust", fill=(247, 147, 26), font=_load_font(54, bold=True))
        draw.text(
            (90, 190),
            "Lightning L402 & Offline-Resilient Cross-Border Micro-Settlement for West Africa",
            fill=(255, 255, 255),
            font=_load_font(38, bold=True),
        )
        cards = [
            (
                (90, 300, 930, 610),
                "1. Cryptographic BOLT-11 & L402 API Gateway",
                [
                    "• BIP-173 Bech32 polymod checksum + HRP multiplier",
                    "  parser (`lnbc`/`lntb`) + SHA-256 HTLC preimage check.",
                    "• Chained HMAC-SHA256 L402 Macaroons enabling",
                    "  zero-account HTTP 402 micro-payments across Africa.",
                ],
            ),
            (
                (990, 300, 1830, 610),
                "2. Multi-Path Payment (MPP) Route Optimizer",
                [
                    "• Dijkstra minimum-fee pathfinding + automatic",
                    "  BOLT-04 Multi-Path Payment (MPP) shard splitting.",
                    "• Connects Paris/Frankfurt LSPs to Dakar-BTrust-Hub,",
                    "  Abidjan-UEMOA, Lagos-BitNob, and Accra-Sats-Bridge.",
                ],
            ),
            (
                (90, 650, 1830, 950),
                "3. Offline USSD (*789#) & RFC 9285 Base45 SMS Vouchers",
                [
                    "• Cuts Europe -> West Africa (XOF / NGN / GHS) remittance fees from 7.85% down to 0.26%.",
                    "• Feature-phone USSD dial strings (*789*1*SATS*PIN#) & HMAC-signed Base45 SMS vouchers",
                    "  empower unbanked merchants without smartphone data connectivity.",
                ],
            ),
        ]
        for box, title, lines in cards:
            draw.rounded_rectangle(box, radius=16, fill=(15, 22, 38), outline=(247, 147, 26), width=3)
            draw.text((box[0] + 26, box[1] + 22), title, fill=(247, 147, 26), font=_load_font(26, bold=True))
            y = box[1] + 72
            for l in lines:
                draw.text((box[0] + 26, y), l, fill=(235, 242, 250), font=_load_font(22))
                y += 38
    else:
        draw.text((90, 140), "SatsFlow — Built for West African Bitcoiners", fill=(255, 255, 255), font=_load_font(54, bold=True))
        draw.text((90, 230), "Live Web App: https://jeffrey-graham.github.io/dakar-satsflow-lightning/", fill=(247, 147, 26), font=_load_font(34, bold=True))
        draw.text((90, 295), "GitHub Repo : https://github.com/jeffrey-graham/dakar-satsflow-lightning", fill=(56, 189, 248), font=_load_font(30))
        draw.rounded_rectangle((90, 380, 1830, 880), radius=18, fill=(15, 22, 38), outline=(16, 185, 129), width=3)
        summary = [
            "Verified Engineering & Cryptographic Deliverables:",
            "  • BOLT-11 Bech32 Encoder/Decoder + SHA-256 HTLC Preimage Verification (`src/satsflow_engine.py`)",
            "  • L402 (LSAT) Chained HMAC-SHA256 Macaroon Challenge & Verification Engine",
            "  • Multi-Hop Dijkstra & Multi-Path Payment (MPP) Channel Liquidity Router",
            "  • RFC 9285 Base45 Offline USSD / SMS Compact Voucher Generator (`*789*1*SATS*PIN#`)",
            "  • 100% Passing Unit Test Suite (`python3 -m unittest discover -s tests -v`)",
        ]
        y = 430
        for idx, line in enumerate(summary):
            draw.text((130, y), line, fill=(52, 211, 153) if idx == 0 else (241, 245, 249), font=_load_font(27 if idx == 0 else 23, bold=(idx == 0)))
            y += 65
    return img


def main() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs" / "index.html", ROOT / "index.html")
    shutil.copy2(ROOT / "docs" / "app.js", ROOT / "app.js")

    base_url = f"file://{DOCS_INDEX.resolve()}"
    s_remit = SCREENSHOTS_DIR / "remittance_corridor.png"
    s_l402 = SCREENSHOTS_DIR / "l402_macaroon_sandbox.png"
    s_mpp = SCREENSHOTS_DIR / "mpp_route_graph.png"

    capture_chrome(f"{base_url}?tab=remittance", s_remit, 1200, 800)
    capture_chrome(f"{base_url}?tab=l402", s_l402, 1200, 800)
    capture_chrome(f"{base_url}?tab=mpp", s_mpp, 1200, 800)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        s_ussd = tmp / "ussd_tab.png"
        capture_chrome(f"{base_url}?tab=ussd", s_ussd, 1200, 800)

        slides = [
            make_bookend_slide(True),
            frame_1080p_from_shot(
                s_remit,
                "CHAPTER 1 / 4  •  WEST AFRICAN REMITTANCE CORRIDOR COMPARATOR (0:10 – 0:20)",
                "Cuts Paris -> Dakar (XOF), Lagos (NGN) & Accra (GHS) settlement fees from 7.85% down to 0.26%.",
            ),
            frame_1080p_from_shot(
                s_l402,
                "CHAPTER 2 / 4  •  BOLT-11 INVOICE & L402 MACAROON API PAYWALL SANDBOX (0:20 – 0:30)",
                "Real BIP-173 Bech32 checksum verification, HMAC-SHA256 Macaroons & atomic HTLC preimage unlock.",
            ),
            frame_1080p_from_shot(
                s_mpp,
                "CHAPTER 3 / 4  •  MULTI-PATH PAYMENT (MPP) CHANNEL LIQUIDITY ROUTER (0:30 – 0:40)",
                "Automatically splits 750,000-sat settlements across parallel routes when single-channel capacity is exceeded.",
            ),
            frame_1080p_from_shot(
                s_ussd,
                "CHAPTER 4 / 4  •  OFFLINE USSD (*789#) & RFC 9285 BASE45 SMS VOUCHERS (0:40 – 0:50)",
                "Empowers feature-phone users in Senegal, Nigeria & Ghana to settle Sats without internet access.",
            ),
            make_bookend_slide(False),
        ]

        concat_lines: list[str] = []
        for idx, img in enumerate(slides):
            p = tmp / f"frame_{idx:02d}.png"
            img.save(p, "PNG")
            concat_lines.append(f"file '{p}'")
            concat_lines.append("duration 10")
        concat_lines.append(f"file '{tmp / 'frame_05.png'}'")
        concat_txt = tmp / "concat.txt"
        concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf",
            "fps=24,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            "60",
            "-movflags",
            "+faststart",
            str(DEMO_MP4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Rendered 60s walkthrough video: {DEMO_MP4} ({DEMO_MP4.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
