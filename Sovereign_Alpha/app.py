#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║          SOVEREIGN ALPHA — Cloud API Service v1.0                  ║
║    FastAPI wrapper for Monitor + Solver + Bridge pipeline           ║
║    Deploy to Railway / Render for 24/7 global yield surveillance   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from hive_mind_network import HiveMindProtocol, PROTOCOL_TOKENS_SYMBOL
from solver_auction_house import AuctionHouse
from zair_audit_ledger import init_db, log_decision, get_audit_history
from zair_protocol_engine import ZairVault
from sovereign_executor_bridge import (
    execute_bridge,
    DEFAULT_SAFE_ADDRESS,
    DEFAULT_ARCHITECT_WALLET,
    DEFAULT_USDC_TOKEN,
    DEFAULT_ALLOCATION_USD,
    PROTOCOL_TAX_PCT,
)
from sovereign_intent_solver import (
    parse_intent,
    simulate_tvl_24h_changes,
    solve_intent,
    sign_solver_output,
    RISK_FREE_POOLS,
)
from sovereign_yield_monitor import (
    RWA_PROTOCOLS,
    MANAGEMENT_FEE_PCT,
    FRED_CACHED_YIELD,
    FRED_CACHED_DATE,
    FRED_API_KEY_DEFAULT,
    fetch_treasury_yield_fred,
    simulate_rwa_yields,
    calculate_sovereign_profit,
    calculate_hourly_tax,
    sign_report,
    verify_report_signature,
    build_report,
    SIGNING_KEY_ENV,
)
import json
import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
#  Ensure project modules are importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
#  App Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sovereign Alpha",
    description="24/7 RWA Yield Monitor & Intent Execution Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache
_cache = {"last_update": 0, "data": None, "ttl": 300}  # 5 min TTL

# Real-time tick history (stores last 500 ticks for chart)
_tick_history = []
_tick_base_spreads = {}  # Initialized on first pipeline run

# Global ZAIR Protocol Vault
zair_vault = ZairVault(initial_aum=10_000_000.0)

# Initialize Audit Ledger
init_db()

# Initialize Hive Mind Network (Federated Risk Intelligence)
hive_protocol = HiveMindProtocol(workspace_dir=str(Path(__file__).parent))


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def get_treasury_yield():
    api_key = os.environ.get("FRED_API_KEY", "") or FRED_API_KEY_DEFAULT
    if api_key:
        result = fetch_treasury_yield_fred(api_key)
        if result is not None:
            return result, "FRED API (LIVE)"
    return FRED_CACHED_YIELD, f"FRED CACHED ({FRED_CACHED_DATE})"


def run_full_pipeline(
    intent_text: str = "balanced yield, moderate risk",
    portfolio_usd: float = 10_000_000,
    allocation_usd: float = 1_000_000,
):
    """Run the complete Monitor → Solver → Bridge pipeline."""
    now = time.time()

    # Check cache
    if _cache["data"] and (now - _cache["last_update"]) < _cache["ttl"]:
        return _cache["data"]

    signing_key = os.environ.get(SIGNING_KEY_ENV, "")

    # Step 1: Monitor
    treasury_yield, treasury_source = get_treasury_yield()
    rwa_yields = simulate_rwa_yields()
    monitor_report = build_report(
        treasury_yield, rwa_yields, portfolio_usd, treasury_source,
        signing_key=signing_key or None,
    )

    # Step 2: Solver
    intent = parse_intent(intent_text)
    tvl_changes = simulate_tvl_24h_changes()
    solver_result = solve_intent(
        intent, treasury_yield, rwa_yields, tvl_changes)
    if zair_vault.agent_private_key:
        solver_result["oracle_signature"] = sign_solver_output(
            solver_result, zair_vault.agent_private_key)

    # Step 2.5: Solver Auction House (Live Marketplace)
    house = AuctionHouse(portfolio_usd)
    auction_result = house.run_auction(rwa_yields, treasury_yield)

    # Step 3: Bridge
    bridge_result = execute_bridge(
        solver_output=solver_result,
        safe_address=os.environ.get("SAFE_ADDRESS", DEFAULT_SAFE_ADDRESS),
        architect_wallet=os.environ.get(
            "ARCHITECT_WALLET", DEFAULT_ARCHITECT_WALLET),
        usdc_token=DEFAULT_USDC_TOKEN,
        allocation_usd=allocation_usd,
        signing_key=signing_key or None,
    )

    # ZAIR Vault processing
    zair_result = zair_vault.rebalance(solver_result)

    # Immutable Audit Logging
    on_chain = zair_result.get("on_chain_data", {})
    log_decision(
        intent=intent_text,
        ondo_apy=on_chain.get("ondo_usdy_apy", 5.35),
        aave_borrow=on_chain.get("aave_usdc_borrow", 5.0),
        spread=on_chain.get("realized_spread_pct", 0.35),
        action=solver_result.get("action", "UNKNOWN"),
        agent_signature=zair_result.get("agent_signature", "")
    )

    combined = {
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "epoch_utc": int(time.time()),
        "monitor": monitor_report,
        "solver": solver_result,
        "auction_house": auction_result,
        "bridge": bridge_result,
        "zair_vault": zair_result,
    }

    _cache["data"] = combined
    _cache["last_update"] = now
    return combined


# ---------------------------------------------------------------------------
#  API Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<html><head><meta http-equiv="refresh" content="0;url=/status"></head></html>"""


@app.get("/api/audit-trail")
async def api_audit_trail():
    """Returns the immutable ZAIR decision ledger."""
    return JSONResponse(content={"history": get_audit_history()})


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sovereign-alpha", "uptime": int(time.time())}


@app.get("/api/monitor")
async def api_monitor(portfolio: float = 10_000_000):
    treasury_yield, source = get_treasury_yield()
    rwa_yields = simulate_rwa_yields()
    signing_key = os.environ.get(SIGNING_KEY_ENV, "")
    report = build_report(treasury_yield, rwa_yields,
                          portfolio, source, signing_key or None)
    return JSONResponse(content=report)


@app.get("/api/solve")
async def api_solve(intent: str = "balanced yield, moderate risk"):
    data = run_full_pipeline(
        intent_text=intent, portfolio_usd=zair_vault.total_assets)
    return JSONResponse(content=data["solver"])


@app.get("/api/bridge")
async def api_bridge(intent: str = "balanced yield", amount: float = 1_000_000):
    data = run_full_pipeline(
        intent_text=intent, portfolio_usd=zair_vault.total_assets, allocation_usd=amount)
    return JSONResponse(content=data["bridge"])


@app.get("/api/pipeline")
async def api_pipeline(
    intent: str = "balanced yield, moderate risk",
    amount: float = 1_000_000,
):
    # Vault handles global portfolio
    data = run_full_pipeline(intent, zair_vault.total_assets, amount)
    return JSONResponse(content=data)


@app.post("/api/deposit")
async def api_deposit(amount: float = 1_000_000.0):
    """Mock ZAIR Deposit."""
    shares = zair_vault.deposit(amount)
    return {"status": "success", "deposited_usd": amount, "shares_minted": shares, "new_total_assets": zair_vault.total_assets}


@app.post("/api/withdraw")
async def api_withdraw(amount: float = 1_000_000.0):
    """Mock ZAIR Withdraw."""
    shares = zair_vault.withdraw(amount)
    return {"status": "success", "withdrawn_usd": amount, "shares_burned": shares, "new_total_assets": zair_vault.total_assets}


@app.get("/api/tick")
async def api_tick():
    """Return a real-time yield tick for live chart updates.

    Generates a new data point with realistic micro-fluctuations
    based on the last full pipeline run's spread data.
    """
    global _tick_base_spreads

    # Initialize base spreads from pipeline cache if needed
    if not _tick_base_spreads and _cache.get("data"):
        mon = _cache["data"].get("monitor", {})
        tr = (mon.get("treasury_benchmark", {}).get("yield_pct", 4.47))
        for p in mon.get("protocols", []):
            pl = p.get("profit_loss", {})
            _tick_base_spreads[p["protocol"]] = pl.get(
                "rwa_yield_pct", 5.0) - tr

    # If still empty, use defaults
    if not _tick_base_spreads:
        _tick_base_spreads = {
            "Ondo Finance (USDY)": 0.6,
            "BlackRock BUIDL": 0.4,
            "Centrifuge (CFG)": 3.2,
        }

    now = int(time.time())
    tick = {"time": now, "spreads": {}}

    for name, base in _tick_base_spreads.items():
        # Realistic micro-fluctuation: ±0.05% jitter
        noise = random.gauss(0, 0.02) + 0.005 * random.choice([-1, 1])
        tick["spreads"][name] = round(max(0, base + noise), 4)

    # Store in history (keep last 500)
    _tick_history.append(tick)
    if len(_tick_history) > 500:
        _tick_history.pop(0)

    return JSONResponse(content=tick)


@app.get("/api/tick/history")
async def api_tick_history():
    """Return full tick history for chart backfill."""
    return JSONResponse(content={"ticks": _tick_history})


# ---------------------------------------------------------------------------
#  HIVE MIND NETWORK APIs (Federated Risk Intelligence + Proof of Alpha)
# ---------------------------------------------------------------------------

@app.get("/api/hive/network-status")
async def hive_network_status():
    """Get real-time Hive Mind Network status and node performance."""
    status = hive_protocol.get_network_status()
    return JSONResponse(content=status)


@app.get("/api/hive/leaderboard")
async def hive_leaderboard():
    """Get ranked leaderboard of nodes by performance (tokens mined, accuracy)."""
    leaderboard = hive_protocol.get_leaderboard()
    return JSONResponse(content={"leaderboard": leaderboard, "token_symbol": PROTOCOL_TOKENS_SYMBOL})


@app.post("/api/hive/submit-asset")
async def hive_submit_asset(
    asset_id: str = "RWA001",
    asset_name: str = "Unknown Asset",
    legal_risk: float = 50,
    liquidity_risk: float = 50,
    smart_contract_risk: float = 50,
    counterparty_risk: float = 50,
    yield_sustainability: float = 50,
    actual_stability: bool = True,
):
    """
    Submit an RWA asset for federated node inference.
    Nodes run local inference, aggregate consensus, and earn PoA tokens.
    """
    asset = {
        "id": asset_id,
        "name": asset_name,
        "legal_risk": legal_risk,
        "liquidity_risk": liquidity_risk,
        "smart_contract_risk": smart_contract_risk,
        "counterparty_risk": counterparty_risk,
        "yield_sustainability": yield_sustainability,
    }

    actual_outcome = {
        "asset_stability": actual_stability,
        "yield_achieved": random.uniform(3, 8),
    }

    result = hive_protocol.process_asset(asset, actual_outcome)

    # Log to audit trail
    log_decision(
        intent=f"Hive Mind: {asset_name}",
        ondo_apy=random.uniform(4.5, 5.5),
        aave_borrow=random.uniform(4.5, 5.5),
        spread=result["consensus"]["consensus_composite_risk"],
        action="HIVE_INFERENCE",
        agent_signature=f"hive-{asset_id}-{int(time.time())}"
    )

    return JSONResponse(content=result)


@app.get("/api/hive/training-dataset")
async def hive_training_dataset(limit: int = 100):
    """
    Retrieve the model recycling dataset (training_dataset.jsonl).
    This is the aggregated 'human/AI hive mind' data for future RLHF.
    """
    dataset_path = Path(__file__).parent / "training_dataset.jsonl"

    if not dataset_path.exists():
        return JSONResponse(content={
            "records": [],
            "total_records": 0,
            "file_path": str(dataset_path),
            "status": "no training data yet"
        })

    records = []
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                records.append(json.loads(line))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    return JSONResponse(content={
        "records": records,
        "total_records": len(records),
        "file_path": str(dataset_path),
        "limit": limit,
    })


@app.get("/api/hive/node/{node_name}")
async def hive_node_stats(node_name: str):
    """
    Get individual node statistics and reward history.
    """
    if node_name not in hive_protocol.nodes:
        return JSONResponse(
            content={"error": f"Node '{node_name}' not found"},
            status_code=404
        )

    node = hive_protocol.nodes[node_name]
    stats = node.get_stats()

    # Serialize rewards
    recent_rewards = []
    for r in node.historical_rewards[-10:]:
        recent_rewards.append({
            "node_name": r.node_name,
            "timestamp": r.timestamp,
            "asset_id": r.asset_id,
            "accuracy_score": r.accuracy_score,
            "predicted_stability": r.predicted_stability,
            "tokens_mined": r.tokens_mined,
            "reward_tier": r.reward_tier,
        })

    return JSONResponse(content={
        **stats,
        "recent_rewards": recent_rewards,
    })


@app.get("/status", response_class=HTMLResponse)
async def status_page(intent: str = "balanced yield, moderate risk"):
    """Serve the mobile-friendly dashboard."""
    data = run_full_pipeline(intent_text=intent)
    html_path = Path(__file__).parent / "templates" / "status.html"
    if html_path.exists():
        template = html_path.read_text(encoding="utf-8")
        # Inject data as JSON into the template
        template = template.replace(
            "__PIPELINE_DATA__", json.dumps(data, ensure_ascii=False))
        return HTMLResponse(content=template)
    else:
        return HTMLResponse(content=f"<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
