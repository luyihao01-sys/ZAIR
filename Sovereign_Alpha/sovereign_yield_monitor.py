#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║               SOVEREIGN YIELD MONITOR v1.1                         ║
║         Real-World Asset (RWA) vs US Treasury Yield Analyzer       ║
║         + HMAC-SHA256 Cryptographic Signing (Oracle Layer)         ║
║                                                                    ║
║  Author:  Sovereign Architect                                      ║
║  Purpose: Monitor RWA protocol yields against the 10Y US Treasury  ║
║           benchmark, calculate net profit after management fees,    ║
║           and report hourly "tax extraction" rates.                 ║
║           All reports are cryptographically signed for verifiable   ║
║           oracle integrity.                                        ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    # Set your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
    set FRED_API_KEY=your_api_key_here          # Windows
    export FRED_API_KEY=your_api_key_here        # Linux/Mac

    # Set your oracle signing key (any secret string)
    set SOVEREIGN_SIGNING_KEY=my_secret_key     # Windows
    export SOVEREIGN_SIGNING_KEY=my_secret_key   # Linux/Mac

    python sovereign_yield_monitor.py

    # Or pass a simulated Treasury yield directly (no API key needed):
    python sovereign_yield_monitor.py --simulate-treasury 4.38
"""

import json
import os
import sys
import time
import random
import hmac
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
#  Windows console UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

FRED_SERIES_ID = "DGS10"  # 10-Year Treasury Constant Maturity Rate
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY_DEFAULT = "925dd7fbef29ffbf5322127a5c9c79a6"  # Your registered key

# Cached real FRED data — used when network is unreachable (e.g. China mainland)
# Last verified: 2026-05-17 via FRED API
FRED_CACHED_YIELD = 4.47   # DGS10 observation date: 2026-05-14
FRED_CACHED_DATE = "2026-05-14"

MANAGEMENT_FEE_PCT = 2.0  # 2% annual management fee

# Top 3 RWA Protocol definitions with realistic yield ranges (annualized %)
RWA_PROTOCOLS = {
    "Ondo Finance (USDY)": {
        "description": "Tokenized short-duration US Treasuries — retail & DeFi composable",
        "chain": "Ethereum / Solana / Mantle",
        "min_yield": 4.80,
        "max_yield": 5.35,
        "tvl_usd": 650_000_000,
    },
    "BlackRock BUIDL": {
        "description": "USD Institutional Digital Liquidity Fund — institutional grade",
        "chain": "Ethereum (Securitize)",
        "min_yield": 4.50,
        "max_yield": 5.25,
        "tvl_usd": 1_800_000_000,
    },
    "Centrifuge (CFG)": {
        "description": "Tokenized private credit — SME trade finance & invoices",
        "chain": "Centrifuge Chain / Ethereum",
        "min_yield": 6.50,
        "max_yield": 9.20,
        "tvl_usd": 280_000_000,
    },
}

# Assumed portfolio size for hourly "tax" calculation
DEFAULT_PORTFOLIO_USD = 10_000_000  # $10M sovereign portfolio


# ---------------------------------------------------------------------------
#  FRED API — Fetch 10Y Treasury Yield
# ---------------------------------------------------------------------------

def fetch_treasury_yield_fred(api_key: str) -> Optional[float]:
    """Fetch the latest 10-Year US Treasury yield from FRED API."""
    try:
        import requests as req_lib

        params = {
            "series_id": FRED_SERIES_ID,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }

        resp = req_lib.get(
            FRED_API_BASE,
            params=params,
            headers={"User-Agent": "SovereignYieldMonitor/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        observations = data.get("observations", [])
        for obs in observations:
            value = obs.get("value", ".")
            if value != ".":
                return float(value)

        print("  [WARN] FRED returned observations but no valid numeric values.")
        return None

    except Exception as e:
        print(f"  [ERROR] Failed to fetch from FRED API: {e}")
        return None


# ---------------------------------------------------------------------------
#  RWA Protocol Yield Simulation
# ---------------------------------------------------------------------------

def simulate_rwa_yields() -> list[dict]:
    """
    Simulate real-time yields for Top 3 RWA protocols.

    In production this would query on-chain smart contracts or protocol APIs.
    Here we generate realistic values within documented yield bands, with minor
    random fluctuation to mimic live market conditions.
    """
    results = []
    for name, meta in RWA_PROTOCOLS.items():
        # Simulate current yield within the documented band
        mid = (meta["min_yield"] + meta["max_yield"]) / 2
        spread = (meta["max_yield"] - meta["min_yield"]) / 2
        jitter = random.gauss(0, spread * 0.25)
        current_yield = round(max(meta["min_yield"], min(meta["max_yield"], mid + jitter)), 4)

        results.append({
            "protocol": name,
            "description": meta["description"],
            "chain": meta["chain"],
            "current_yield_pct": current_yield,
            "yield_range_pct": f"{meta['min_yield']:.2f} – {meta['max_yield']:.2f}",
            "tvl_usd": meta["tvl_usd"],
        })

    return results


# ---------------------------------------------------------------------------
#  Core Calculation Engine
# ---------------------------------------------------------------------------

def calculate_sovereign_profit(
    rwa_yield_pct: float,
    treasury_yield_pct: float,
    management_fee_pct: float = MANAGEMENT_FEE_PCT,
) -> dict:
    """
    Core P&L formula:
        Net Profit (%) = RWA Yield - Treasury Yield - Management Fee

    A positive result means the RWA protocol generates alpha above the
    risk-free rate after the architect's management fee is deducted.
    """
    net_profit_pct = round(rwa_yield_pct - treasury_yield_pct - management_fee_pct, 4)
    return {
        "rwa_yield_pct": rwa_yield_pct,
        "treasury_yield_pct": treasury_yield_pct,
        "management_fee_pct": management_fee_pct,
        "net_profit_pct": round(net_profit_pct, 4),
        "profitable": net_profit_pct > 0,
    }


def calculate_hourly_tax(net_annual_pct: float, portfolio_usd: float) -> dict:
    """
    Convert annualized net profit % into an hourly 'tax extraction' amount.

    Hours per year ≈ 8,760
    """
    HOURS_PER_YEAR = 8_760
    if net_annual_pct <= 0:
        return {
            "hourly_extraction_usd": 0.0,
            "daily_extraction_usd": 0.0,
            "annual_extraction_usd": 0.0,
            "portfolio_usd": portfolio_usd,
        }

    annual_usd = portfolio_usd * (net_annual_pct / 100)
    hourly_usd = annual_usd / HOURS_PER_YEAR
    daily_usd = hourly_usd * 24

    return {
        "hourly_extraction_usd": round(hourly_usd, 2),
        "daily_extraction_usd": round(daily_usd, 2),
        "annual_extraction_usd": round(annual_usd, 2),
        "portfolio_usd": portfolio_usd,
    }


# ---------------------------------------------------------------------------
#  Cryptographic Signing — HMAC-SHA256 Oracle Layer
# ---------------------------------------------------------------------------

SIGNING_KEY_ENV = "SOVEREIGN_SIGNING_KEY"
SIGNING_ALGORITHM = "HMAC-SHA256"


def _canonical_json(obj: dict) -> str:
    """Produce a deterministic JSON string for signing.

    Uses sorted keys and no whitespace to ensure the same input always
    produces the same byte sequence, regardless of platform or Python
    dict ordering.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sign_report(report: dict, signing_key: str) -> dict:
    """Generate an HMAC-SHA256 signature over the report's summary payload.

    The signed payload consists of the canonical JSON of the *summary*
    block plus the *epoch_utc* timestamp, binding the signature to both
    the data and the moment it was produced.

    Returns a dict to be embedded as report["oracle_signature"].
    """
    # Build the payload that gets signed
    signed_payload = {
        "epoch_utc": report["epoch_utc"],
        "summary": report["summary"],
        "treasury_yield_pct": report["treasury_benchmark"]["yield_pct"],
    }
    canonical = _canonical_json(signed_payload)

    # HMAC-SHA256
    sig = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "algorithm": SIGNING_ALGORITHM,
        "signed_fields": ["epoch_utc", "summary", "treasury_yield_pct"],
        "canonical_payload": canonical,
        "signature": sig,
        "signer": "sovereign-architect-oracle",
        "key_source": f"env:{SIGNING_KEY_ENV}",
    }


def verify_report_signature(report: dict, signing_key: str) -> bool:
    """Verify the HMAC-SHA256 signature embedded in a report.

    This allows any party with the shared key to confirm that the
    summary data has not been tampered with since signing.
    """
    sig_block = report.get("oracle_signature")
    if not sig_block:
        return False

    canonical = sig_block.get("canonical_payload", "")
    expected_sig = sig_block.get("signature", "")

    computed = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected_sig)


# ---------------------------------------------------------------------------
#  Report Builder
# ---------------------------------------------------------------------------

def build_report(
    treasury_yield: float,
    rwa_yields: list[dict],
    portfolio_usd: float,
    treasury_source: str,
    signing_key: Optional[str] = None,
) -> dict:
    """Assemble the full JSON report, optionally with oracle signature."""

    now = datetime.now(timezone(timedelta(hours=8)))  # UTC+8
    protocols = []
    total_hourly = 0.0

    for rwa in rwa_yields:
        pnl = calculate_sovereign_profit(rwa["current_yield_pct"], treasury_yield)
        tax = calculate_hourly_tax(pnl["net_profit_pct"], portfolio_usd)
        total_hourly += tax["hourly_extraction_usd"]

        protocols.append({
            "protocol": rwa["protocol"],
            "description": rwa["description"],
            "chain": rwa["chain"],
            "current_yield_pct": rwa["current_yield_pct"],
            "yield_range_pct": rwa["yield_range_pct"],
            "tvl_usd": f"${rwa['tvl_usd']:,.0f}",
            "profit_loss": pnl,
            "tax_extraction": tax,
        })

    report = {
        "report_title": "Sovereign Yield Monitor — Architect Tax Report",
        "generated_at": now.isoformat(),
        "epoch_utc": int(time.time()),
        "treasury_benchmark": {
            "series": "US 10-Year Treasury (DGS10)",
            "yield_pct": treasury_yield,
            "source": treasury_source,
        },
        "management_fee_pct": MANAGEMENT_FEE_PCT,
        "portfolio_usd": f"${portfolio_usd:,.0f}",
        "protocols": protocols,
        "summary": {
            "total_hourly_tax_usd": round(total_hourly, 2),
            "total_daily_tax_usd": round(total_hourly * 24, 2),
            "total_annual_tax_usd": round(total_hourly * 8760, 2),
            "profitable_protocols": sum(1 for p in protocols if p["profit_loss"]["profitable"]),
            "total_protocols_analyzed": len(protocols),
        },
    }

    # ── Oracle Signature Layer ──────────────────────────────────────────
    if signing_key:
        report["oracle_signature"] = sign_report(report, signing_key)
    else:
        report["oracle_signature"] = {
            "algorithm": SIGNING_ALGORITHM,
            "signature": None,
            "status": f"UNSIGNED — set {SIGNING_KEY_ENV} env var to enable",
        }

    return report


# ---------------------------------------------------------------------------
#  Pretty Console Output
# ---------------------------------------------------------------------------

def print_banner():
    banner = r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   ⚡  SOVEREIGN YIELD MONITOR  ⚡                          ║
    ║   RWA vs Treasury · Architect Tax Extraction Engine         ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(report: dict):
    """Print a human-readable summary to the console."""
    tb = report["treasury_benchmark"]
    s = report["summary"]

    print(f"  📅  Timestamp     : {report['generated_at']}")
    print(f"  🏦  Treasury (10Y): {tb['yield_pct']:.2f}%  [{tb['source']}]")
    print(f"  💼  Portfolio     : {report['portfolio_usd']}")
    print(f"  🏷️  Mgmt Fee      : {report['management_fee_pct']:.1f}%")
    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  PROTOCOL BREAKDOWN                                     │")
    print("  ├──────────────────────────────────────────────────────────┤")

    for p in report["protocols"]:
        pnl = p["profit_loss"]
        tax = p["tax_extraction"]
        status = "✅" if pnl["profitable"] else "❌"
        sign = "+" if pnl["net_profit_pct"] >= 0 else ""
        print(f"  │  {status} {p['protocol']:<30}")
        print(f"  │     Yield: {pnl['rwa_yield_pct']:.2f}%  │  Net: {sign}{pnl['net_profit_pct']:.2f}%")
        print(f"  │     Hourly Tax: ${tax['hourly_extraction_usd']:>10,.2f}  │  Daily: ${tax['daily_extraction_usd']:>10,.2f}")
        print(f"  │     Chain: {p['chain']}")
        print(f"  │     TVL: {p['tvl_usd']}")
        print("  ├──────────────────────────────────────────────────────────┤")

    print("  │                                                          │")
    print(f"  │  ⚡ TOTAL HOURLY TAX  : ${s['total_hourly_tax_usd']:>12,.2f}             │")
    print(f"  │  📊 TOTAL DAILY TAX   : ${s['total_daily_tax_usd']:>12,.2f}             │")
    print(f"  │  🏆 TOTAL ANNUAL TAX  : ${s['total_annual_tax_usd']:>12,.2f}             │")
    print(f"  │  ✅ Profitable: {s['profitable_protocols']}/{s['total_protocols_analyzed']} protocols                          │")
    print("  └──────────────────────────────────────────────────────────┘")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sovereign Yield Monitor — RWA vs Treasury Tax Engine"
    )
    parser.add_argument(
        "--simulate-treasury",
        type=float,
        default=None,
        help="Skip FRED API and use this simulated 10Y Treasury yield (e.g. 4.38)",
    )
    parser.add_argument(
        "--portfolio",
        type=float,
        default=DEFAULT_PORTFOLIO_USD,
        help=f"Portfolio size in USD (default: ${DEFAULT_PORTFOLIO_USD:,.0f})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save JSON report to this file path (default: print to stdout)",
    )
    args = parser.parse_args()

    print_banner()

    # ── Step 1: Get Treasury yield ──────────────────────────────────────
    treasury_yield = None
    treasury_source = ""

    if args.simulate_treasury is not None:
        treasury_yield = args.simulate_treasury
        treasury_source = "SIMULATED"
        print(f"  [INFO] Using simulated Treasury yield: {treasury_yield:.2f}%\n")
    else:
        api_key = os.environ.get("FRED_API_KEY", "") or FRED_API_KEY_DEFAULT
        if not api_key:
            print("  [WARN] No API key available. Falling back to simulated Treasury yield.")
            print("         Set env var FRED_API_KEY or use --simulate-treasury <rate>\n")
            treasury_yield = 4.38  # Realistic fallback
            treasury_source = "SIMULATED (fallback — no API key)"
        else:
            print("  [INFO] Fetching 10Y Treasury yield from FRED API…")
            treasury_yield = fetch_treasury_yield_fred(api_key)
            if treasury_yield is None:
                treasury_yield = FRED_CACHED_YIELD
                treasury_source = f"FRED CACHED ({FRED_CACHED_DATE} — network unreachable)"
                print(f"  [WARN] API unreachable. Using cached real value: {treasury_yield:.2f}%\n")
            else:
                treasury_source = "FRED API (DGS10) — LIVE"
                print(f"  [OK]   10Y Treasury: {treasury_yield:.2f}%\n")

    # ── Step 2: Simulate RWA yields ─────────────────────────────────────
    print("  [INFO] Fetching RWA protocol yields (simulated live data)…")
    rwa_yields = simulate_rwa_yields()
    print(f"  [OK]   Loaded {len(rwa_yields)} protocols.\n")

    # ── Step 3: Load signing key ─────────────────────────────────────────
    signing_key = os.environ.get(SIGNING_KEY_ENV, "")
    if signing_key:
        print(f"  [INFO] Oracle signing key loaded from ${SIGNING_KEY_ENV}")
    else:
        print(f"  [WARN] {SIGNING_KEY_ENV} not set — report will be UNSIGNED")
        print(f"         Set env var to enable HMAC-SHA256 oracle signatures\n")

    # ── Step 4: Build report ────────────────────────────────────────────
    report = build_report(
        treasury_yield, rwa_yields, args.portfolio, treasury_source,
        signing_key=signing_key or None,
    )

    # ── Step 5: Output ──────────────────────────────────────────────────
    print_summary(report)
    print()

    # Show signature status
    sig = report.get("oracle_signature", {})
    if sig.get("signature"):
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │  🔐 ORACLE SIGNATURE                                    │")
        print("  ├──────────────────────────────────────────────────────────┤")
        print(f"  │  Algorithm : {sig['algorithm']}")
        print(f"  │  Signer    : {sig['signer']}")
        print(f"  │  Signature : {sig['signature'][:32]}…")
        print(f"  │  Status    : ✅ SIGNED & VERIFIABLE")
        print("  └──────────────────────────────────────────────────────────┘")
    else:
        print("  ⚠️  Report is UNSIGNED (set SOVEREIGN_SIGNING_KEY to sign)")
    print()

    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_json)
        print(f"  [OK] JSON report saved to: {args.output}")
    else:
        print("  ═══════════════════ JSON REPORT ═══════════════════")
        print(report_json)

    # ── Step 6: Verify signature round-trip ─────────────────────────────
    if signing_key and sig.get("signature"):
        verified = verify_report_signature(report, signing_key)
        icon = "✅" if verified else "❌"
        print(f"\n  [VERIFY] Signature round-trip check: {icon} {'PASS' if verified else 'FAIL'}")

    print("\n  [DONE] Sovereign Yield Monitor complete. 🏛️\n")


if __name__ == "__main__":
    main()
