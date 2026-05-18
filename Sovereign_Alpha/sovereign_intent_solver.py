#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║            SOVEREIGN INTENT SOLVER v1.0                            ║
║    Natural-Language Intent → Structured DeFi Action Engine         ║
║                                                                    ║
║  Integrates with sovereign_yield_monitor.py to analyze live RWA    ║
║  yields and produce executable, risk-aware allocation intents.     ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    python sovereign_intent_solver.py "目标收益率 5%，安全性最高"
    python sovereign_intent_solver.py "maximize yield, high risk ok"
    python sovereign_intent_solver.py --interactive
"""

import json
import sys
import os
import re
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
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
#  Import monitor components
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sovereign_yield_monitor import (
    RWA_PROTOCOLS,
    MANAGEMENT_FEE_PCT,
    FRED_CACHED_YIELD,
    FRED_CACHED_DATE,
    FRED_API_KEY_DEFAULT,
    fetch_treasury_yield_fred,
    simulate_rwa_yields,
    calculate_sovereign_profit,
)

# ---------------------------------------------------------------------------
#  Constants & Configuration
# ---------------------------------------------------------------------------

# Risk-free fallback pools when RWA spread is too thin
RISK_FREE_POOLS = [
    {
        "protocol": "sDAI (Spark/MakerDAO)",
        "description": "Tokenized DAI Savings Rate — risk-free DeFi benchmark",
        "chain": "Ethereum",
        "yield_pct": 3.50,
        "risk_tier": "MINIMAL",
    },
    {
        "protocol": "Ethena sUSDe",
        "description": "Delta-neutral stablecoin yield via basis trade",
        "chain": "Ethereum",
        "yield_pct": 4.10,
        "risk_tier": "LOW",
    },
    {
        "protocol": "Aave USDC",
        "description": "Blue-chip lending protocol — variable supply rate",
        "chain": "Ethereum / Arbitrum",
        "yield_pct": 3.20,
        "risk_tier": "MINIMAL",
    },
]

# Thresholds
SPREAD_THRESHOLD_PCT = 1.0     # RWA yield - Treasury < 1% → move to risk-free
TVL_DROP_EMERGENCY_PCT = 5.0   # TVL drop >5% in 24h → emergency exit
INTENT_TAX_PCT = 0.05          # ZAIR Protocol autonomous tax applied to yield

# Risk tiers (lower = safer)
RISK_SCORES = {"MINIMAL": 1, "LOW": 2, "MEDIUM": 3, "HIGH": 4, "EXTREME": 5}

# ---------------------------------------------------------------------------
#  Natural Language Intent Parser
# ---------------------------------------------------------------------------

def parse_intent(raw_input: str) -> dict:
    """Parse natural language into a structured intent object.

    Extracts:
      - target_yield_pct: desired minimum yield (if mentioned)
      - risk_preference: LOW / MEDIUM / HIGH
      - priority: "safety" | "yield" | "balanced"
      - language: detected language
    """
    text = raw_input.lower().strip()

    # --- Extract target yield ---
    target_yield = None
    yield_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if yield_match:
        target_yield = float(yield_match.group(1))

    # --- Detect risk preference ---
    safety_keywords = [
        "安全", "保守", "低风险", "稳", "safe", "conservative", "low risk",
        "secure", "stable", "最高安全", "无风险",
    ]
    aggressive_keywords = [
        "激进", "高收益", "最大化", "高风险", "aggressive", "maximize",
        "max yield", "high risk", "risky",
    ]
    balanced_keywords = [
        "平衡", "均衡", "balanced", "moderate", "中等",
    ]

    risk_pref = "MEDIUM"
    priority = "balanced"

    if any(kw in text for kw in safety_keywords):
        risk_pref = "LOW"
        priority = "safety"
    elif any(kw in text for kw in aggressive_keywords):
        risk_pref = "HIGH"
        priority = "yield"
    elif any(kw in text for kw in balanced_keywords):
        risk_pref = "MEDIUM"
        priority = "balanced"

    # --- Detect language ---
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', raw_input))
    lang = "zh-CN" if has_cjk else "en"

    return {
        "raw_input": raw_input,
        "target_yield_pct": target_yield,
        "risk_preference": risk_pref,
        "priority": priority,
        "language": lang,
    }


# ---------------------------------------------------------------------------
#  TVL Monitoring — 24h Drop Simulation
# ---------------------------------------------------------------------------

def simulate_tvl_24h_changes() -> dict:
    """Simulate 24-hour TVL changes for each RWA protocol.

    In production, this would query on-chain data or DeFiLlama API.
    Here we simulate realistic fluctuations, with a small chance of
    a >5% crash to test emergency exit logic.
    """
    changes = {}
    for name, meta in RWA_PROTOCOLS.items():
        # 90% chance: normal fluctuation (-3% to +3%)
        # 10% chance: stress event (-12% to -4%)
        if random.random() < 0.10:
            pct_change = round(random.uniform(-12.0, -4.0), 2)
        else:
            pct_change = round(random.gauss(0.2, 1.5), 2)

        new_tvl = int(meta["tvl_usd"] * (1 + pct_change / 100))
        changes[name] = {
            "tvl_24h_ago": meta["tvl_usd"],
            "tvl_current": new_tvl,
            "change_pct": pct_change,
            "emergency": pct_change <= -TVL_DROP_EMERGENCY_PCT,
        }
    return changes


# ---------------------------------------------------------------------------
#  Core Solver Engine
# ---------------------------------------------------------------------------

def solve_intent(
    intent: dict,
    treasury_yield: float,
    rwa_yields: list[dict],
    tvl_changes: dict,
) -> dict:
    """The core solver: maps a parsed intent to concrete DeFi actions.

    Decision logic:
      1. For each RWA protocol, compute spread = RWA_yield - Treasury_yield
      2. If spread < 1% → recommend risk-free pool instead
      3. If TVL dropped >5% in 24h → EMERGENCY EXIT
      4. Filter & rank by user's risk preference and target yield
    """
    now = datetime.now(timezone(timedelta(hours=8)))
    actions = []
    risk_warnings = []
    emergency_exits = []

    target = intent.get("target_yield_pct")
    risk_pref = intent.get("risk_preference", "MEDIUM")
    priority = intent.get("priority", "balanced")

    # ── Analyze each RWA protocol ───────────────────────────────────────
    for rwa in rwa_yields:
        name = rwa["protocol"]
        rwa_yield = rwa["current_yield_pct"]
        spread = round(rwa_yield - treasury_yield, 4)
        net_profit = round(rwa_yield - treasury_yield - MANAGEMENT_FEE_PCT, 4)

        tvl_info = tvl_changes.get(name, {})
        tvl_drop = tvl_info.get("change_pct", 0)
        is_emergency = tvl_info.get("emergency", False)

        # --- Emergency exit check ---
        if is_emergency:
            emergency_exits.append({
                "action": "EMERGENCY_EXIT",
                "protocol": name,
                "reason": f"TVL dropped {tvl_drop:.1f}% in 24h (threshold: -{TVL_DROP_EMERGENCY_PCT}%)",
                "tvl_24h_ago": f"${tvl_info['tvl_24h_ago']:,.0f}",
                "tvl_current": f"${tvl_info['tvl_current']:,.0f}",
                "urgency": "CRITICAL",
                "recommended_destination": "sDAI (Spark/MakerDAO)",
            })
            risk_warnings.append(
                f"🚨 {name}: TVL crash {tvl_drop:.1f}% — EMERGENCY EXIT triggered"
            )
            continue

        # --- Spread too thin → move to risk-free ---
        if spread < SPREAD_THRESHOLD_PCT:
            risk_warnings.append(
                f"⚠️ {name}: spread {spread:.2f}% < {SPREAD_THRESHOLD_PCT}% threshold — insufficient alpha"
            )
            actions.append({
                "action": "REDIRECT_TO_RISK_FREE",
                "source_protocol": name,
                "reason": f"Spread ({spread:.2f}%) below {SPREAD_THRESHOLD_PCT}% minimum",
                "spread_pct": spread,
                "net_yield_pct": net_profit,
                "recommendation": "Redirect capital to base risk-free pool",
            })
            continue

        # --- Viable protocol: check against user intent ---
        risk_tier = "MEDIUM"
        if rwa_yield < 6.0:
            risk_tier = "LOW"
        elif rwa_yield > 8.0:
            risk_tier = "HIGH"

        # Filter by target yield
        if target and net_profit < 0:
            continue

        # Risk preference filter
        user_risk_score = RISK_SCORES.get(risk_pref, 3)
        protocol_risk_score = RISK_SCORES.get(risk_tier, 3)

        if priority == "safety" and protocol_risk_score > user_risk_score + 1:
            risk_warnings.append(
                f"⚠️ {name}: risk tier {risk_tier} exceeds preference {risk_pref}"
            )
            continue

        actions.append({
            "action": "ALLOCATE",
            "protocol": name,
            "chain": rwa["chain"],
            "current_yield_pct": rwa_yield,
            "treasury_benchmark_pct": treasury_yield,
            "spread_pct": spread,
            "management_fee_pct": MANAGEMENT_FEE_PCT,
            "expected_net_yield_pct": net_profit,
            "risk_tier": risk_tier,
            "tvl_change_24h_pct": tvl_drop,
        })

    # ── Risk-free pool recommendations ──────────────────────────────────
    risk_free_picks = []
    for pool in RISK_FREE_POOLS:
        pool_risk_score = RISK_SCORES.get(pool["risk_tier"], 1)
        user_risk_score = RISK_SCORES.get(risk_pref, 3)

        if priority == "safety" or not actions:
            if pool_risk_score <= user_risk_score:
                net = round(pool["yield_pct"] - MANAGEMENT_FEE_PCT, 2)
                risk_free_picks.append({
                    "action": "ALLOCATE_RISK_FREE",
                    "protocol": pool["protocol"],
                    "description": pool["description"],
                    "chain": pool["chain"],
                    "yield_pct": pool["yield_pct"],
                    "expected_net_yield_pct": net,
                    "risk_tier": pool["risk_tier"],
                })

    # ── Multi-Solver Simulation & Path Evaluation ───────────────────────
    # We simulate 3 distinct solvers proposing different paths.
    alpha_actions = list(actions)
    beta_actions = list(actions)
    gamma_actions = list(actions)

    # Solver Alpha (Balanced): Sorts by spread matching
    alpha_actions.sort(key=lambda x: x.get("spread_pct", 0), reverse=True)
    
    # Solver Beta (Safety): Prioritizes lowest risk tier, then yield
    beta_actions.sort(key=lambda x: (RISK_SCORES.get(x.get("risk_tier", "MEDIUM"), 3), -x.get("expected_net_yield_pct", 0)))
    
    # Solver Gamma (Max Yield): Pure yield maximization
    gamma_actions.sort(key=lambda x: x.get("expected_net_yield_pct", 0), reverse=True)

    def get_top_pick(sorted_actions):
        return sorted_actions[0] if sorted_actions else (risk_free_picks[0] if risk_free_picks else None)

    competitors = {
        "Alpha (Balanced)": get_top_pick(alpha_actions),
        "Beta (Safety)": get_top_pick(beta_actions),
        "Gamma (Yield)": get_top_pick(gamma_actions)
    }

    # evaluate_best_path logic based on intent priority
    best_solver_name = "Alpha (Balanced)"
    if emergency_exits:
        best_action = emergency_exits[0]
        best_solver_name = "Emergency Override"
    else:
        if priority == "safety":
            best_solver_name = "Beta (Safety)"
        elif priority == "yield":
            best_solver_name = "Gamma (Yield)"
        else:
            best_solver_name = "Alpha (Balanced)"
        
        best_action = competitors[best_solver_name]

    # Apply 0.05% Intent Tax automatically for ZAIR Protocol
    if best_action and best_action.get("action") == "ALLOCATE":
        best_action = dict(best_action)  # avoid mutating shared dicts
        best_action["expected_net_yield_pct"] = round(best_action["expected_net_yield_pct"] - INTENT_TAX_PCT, 4)
        best_action["intent_tax_applied_pct"] = INTENT_TAX_PCT

    result = {
        "solver_title": "Sovereign Intent Solver — Action Report",
        "generated_at": now.isoformat(),
        "epoch_utc": int(time.time()),
        "intent": intent,
        "market_context": {
            "treasury_10y_yield_pct": treasury_yield,
            "spread_threshold_pct": SPREAD_THRESHOLD_PCT,
            "tvl_emergency_threshold_pct": TVL_DROP_EMERGENCY_PCT,
            "management_fee_pct": MANAGEMENT_FEE_PCT,
            "intent_tax_pct": INTENT_TAX_PCT,
        },
        "primary_recommendation": best_action,
        "multi_solver_competition": competitors,
        "winning_solver": best_solver_name,
        "all_actions": actions,
        "emergency_exits": emergency_exits,
        "risk_free_alternatives": risk_free_picks,
        "risk_warnings": risk_warnings,
        "tvl_monitor": tvl_changes,
        "summary": {
            "total_protocols_analyzed": len(rwa_yields),
            "viable_allocations": len(actions),
            "emergency_exits_triggered": len(emergency_exits),
            "risk_free_alternatives_available": len(risk_free_picks),
            "risk_warnings_count": len(risk_warnings),
        },
    }

    return result


# ---------------------------------------------------------------------------
#  EIP-712 Ethereum Intent Signing
# ---------------------------------------------------------------------------

def sign_solver_output(result: dict, agent_private_key: str) -> dict:
    """Sign the solver intent using EIP-712 standard for smart contract verification."""
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    
    action = result.get("primary_recommendation", {}).get("action", "UNKNOWN")
    protocol = result.get("primary_recommendation", {}).get("protocol", "UNKNOWN")
    expected_net = result.get("primary_recommendation", {}).get("expected_net_yield_pct", 0)
    
    # Scale yield to int for Solidity, e.g. 5.35% -> 535
    scaled_yield = int(expected_net * 100) if expected_net else 0

    domain_data = {
        "name": "ZAIR Protocol",
        "version": "1",
        "chainId": 1,
    }
    message_types = {
        "Intent": [
            {"name": "epoch", "type": "uint256"},
            {"name": "action", "type": "string"},
            {"name": "targetProtocol", "type": "string"},
            {"name": "expectedNetYield", "type": "int256"},
        ]
    }
    message_data = {
        "epoch": result["epoch_utc"],
        "action": action,
        "targetProtocol": protocol,
        "expectedNetYield": scaled_yield,
    }
    
    signable_message = encode_typed_data(domain_data, message_types, message_data)
    acct = Account.from_key(agent_private_key)
    signed_message = acct.sign_message(signable_message)
    
    return {
        "algorithm": "EIP-712",
        "signed_fields": ["epoch", "action", "targetProtocol", "expectedNetYield"],
        "signature": "0x" + signed_message.signature.hex(),
        "signer": acct.address,
    }


# ---------------------------------------------------------------------------
#  Pretty Console Output
# ---------------------------------------------------------------------------

def print_banner():
    print(r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🧠  SOVEREIGN INTENT SOLVER  🧠                         ║
    ║   Natural Language → DeFi Action Engine                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def print_result(result: dict):
    intent = result["intent"]
    ctx = result["market_context"]
    s = result["summary"]

    print(f"  📝  Input       : {intent['raw_input']}")
    print(f"  🎯  Priority    : {intent['priority'].upper()}")
    print(f"  🛡️  Risk Pref   : {intent['risk_preference']}")
    if intent["target_yield_pct"]:
        print(f"  💰  Target Yield: {intent['target_yield_pct']}%")
    print(f"  🏦  Treasury    : {ctx['treasury_10y_yield_pct']:.2f}%")
    print()

    # Emergency exits
    if result["emergency_exits"]:
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │  🚨 EMERGENCY EXITS                                     │")
        print("  ├──────────────────────────────────────────────────────────┤")
        for ex in result["emergency_exits"]:
            print(f"  │  Protocol : {ex['protocol']}")
            print(f"  │  TVL      : {ex['tvl_24h_ago']} → {ex['tvl_current']}")
            print(f"  │  Reason   : {ex['reason']}")
            print(f"  │  Evacuate → {ex['recommended_destination']}")
            print("  ├──────────────────────────────────────────────────────────┤")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

    # Multi-Solver Output
    comps = result.get("multi_solver_competition", {})
    if comps:
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │  🏁 MULTI-SOLVER COMPETITION                             │")
        print("  ├──────────────────────────────────────────────────────────┤")
        for s_name, s_rec in comps.items():
            if not s_rec: continue
            proto = s_rec.get("protocol", "N/A")
            net_y = s_rec.get("expected_net_yield_pct", 0)
            mark = "🏆" if s_name == result.get("winning_solver") else "  "
            print(f"  │ {mark} {s_name:<16}: {proto:<20} ({net_y:+.2f}%)")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

    # Primary recommendation
    rec = result["primary_recommendation"]
    if rec:
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │  ⚡ OPTIMAL PATH SELECTED                                │")
        print("  ├──────────────────────────────────────────────────────────┤")
        print(f"  │  Winner   : {result.get('winning_solver', 'N/A')}")
        print(f"  │  Action   : {rec.get('action', 'N/A')}")
        print(f"  │  Protocol : {rec.get('protocol', rec.get('source_protocol', 'N/A'))}")
        net = rec.get('expected_net_yield_pct', 'N/A')
        if isinstance(net, (int, float)):
            sign = "+" if net >= 0 else ""
            print(f"  │  Net Yield: {sign}{net:.2f}% (After Protocol Fees)")
            
        tax = rec.get('intent_tax_applied_pct')
        if tax:
            print(f"  │  ZAIR Tax : -{tax:.2f}% (Intent Routing Fee)")
            
        print(f"  │  Risk     : {rec.get('risk_tier', rec.get('urgency', 'N/A'))}")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

    # Risk warnings
    if result["risk_warnings"]:
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │  ⚠️  RISK WARNINGS                                      │")
        print("  ├──────────────────────────────────────────────────────────┤")
        for w in result["risk_warnings"]:
            print(f"  │  {w}")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

    # Summary
    print(f"  📊  Protocols analyzed : {s['total_protocols_analyzed']}")
    print(f"  ✅  Viable allocations : {s['viable_allocations']}")
    print(f"  🚨  Emergency exits    : {s['emergency_exits_triggered']}")
    print(f"  🏦  Risk-free options  : {s['risk_free_alternatives_available']}")
    print(f"  ⚠️  Risk warnings      : {s['risk_warnings_count']}")


# ---------------------------------------------------------------------------
#  Treasury Yield Helper
# ---------------------------------------------------------------------------

def get_treasury_yield() -> tuple[float, str]:
    """Try FRED API, fall back to cached value."""
    api_key = os.environ.get("FRED_API_KEY", "") or FRED_API_KEY_DEFAULT
    if api_key:
        result = fetch_treasury_yield_fred(api_key)
        if result is not None:
            return result, "FRED API (LIVE)"
    return FRED_CACHED_YIELD, f"FRED CACHED ({FRED_CACHED_DATE})"


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sovereign Intent Solver — NL → DeFi Action Engine"
    )
    parser.add_argument(
        "intent",
        nargs="?",
        default=None,
        help='Natural language intent, e.g. "目标收益率 5%%，安全性最高"',
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (prompt for input)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save JSON result to file",
    )
    args = parser.parse_args()

    print_banner()

    # ── Get intent ──────────────────────────────────────────────────────
    if args.intent:
        raw_intent = args.intent
    elif args.interactive:
        raw_intent = input("  🧠  Enter your intent > ").strip()
    else:
        raw_intent = "目标收益率 5%，安全性最高"
        print(f"  [INFO] No intent provided. Using default: \"{raw_intent}\"\n")

    intent = parse_intent(raw_intent)
    print(f"  [OK] Intent parsed: priority={intent['priority']}, risk={intent['risk_preference']}\n")

    # ── Fetch market data ───────────────────────────────────────────────
    print("  [INFO] Fetching Treasury yield…")
    treasury_yield, source = get_treasury_yield()
    print(f"  [OK]   10Y Treasury: {treasury_yield:.2f}% [{source}]\n")

    print("  [INFO] Fetching RWA protocol yields…")
    rwa_yields = simulate_rwa_yields()
    print(f"  [OK]   {len(rwa_yields)} protocols loaded.\n")

    print("  [INFO] Monitoring TVL changes (24h)…")
    tvl_changes = simulate_tvl_24h_changes()
    for name, info in tvl_changes.items():
        icon = "🚨" if info["emergency"] else "📊"
        print(f"  {icon}  {name}: {info['change_pct']:+.2f}%")
    print()

    # ── Solve ───────────────────────────────────────────────────────────
    result = solve_intent(intent, treasury_yield, rwa_yields, tvl_changes)

    # ── Sign ────────────────────────────────────────────────────────────
    # Load or generate ZAIR_AGENT_PK
    agent_private_key = None
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("ZAIR_AGENT_PK="):
                    agent_private_key = line.split("=")[1].strip()
                    break
    
    if not agent_private_key:
        from eth_account import Account
        acct = Account.create()
        agent_private_key = acct.key.hex()
        with open(env_path, "a") as f:
            f.write(f"\nZAIR_AGENT_PK={agent_private_key}\n")

    result["oracle_signature"] = sign_solver_output(result, agent_private_key)
    print("  [OK] EIP-712 Ethereum Signature applied.\n")

    # ── Output ──────────────────────────────────────────────────────────
    print_result(result)
    print()

    result_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result_json)
        print(f"  [OK] JSON saved to: {args.output}")
    else:
        print("  ═══════════════════ JSON RESULT ═══════════════════")
        print(result_json)

    print("\n  [DONE] Sovereign Intent Solver complete. 🧠\n")


if __name__ == "__main__":
    main()
