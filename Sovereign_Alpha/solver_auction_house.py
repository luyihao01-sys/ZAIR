import time
import random
from datetime import datetime, timezone

ROUTING_TAX_PCT = 0.05

from zair_audit_ledger import log_decision

class AuctionHouse:
    def __init__(self, portfolio_usd: float):
        self.portfolio_usd = portfolio_usd
        self.tax_rate = 0.0005 # 0.05% routing tax

    def run_auction(self, rwa_yields: list, treasury_yield: float) -> dict:
        """
        Simulates a decentralized solver marketplace auction.
        3 Solvers compete to provide the best execution path.
        """
        if not rwa_yields:
            return {}

        sorted_rwas = sorted(rwa_yields, key=lambda x: x["current_yield_pct"], reverse=True)
        
        internal_pick = sorted_rwas[0] if len(sorted_rwas) > 0 else None
        quant_pick = sorted_rwas[min(1, len(sorted_rwas)-1)]
        whale_pick = sorted_rwas[0]

        bids = []
        
        # Solver 1: Internal Agent (No tax)
        if internal_pick:
            gross_yield = internal_pick["current_yield_pct"]
            est_slip = round(random.uniform(0.05, 0.10), 4)
            gas_cost = round(random.uniform(0.01, 0.05), 4)
            net_apy = gross_yield - treasury_yield - est_slip - gas_cost
            bids.append({
                "solver": "Internal Agent",
                "protocol_path": internal_pick["protocol"],
                "gross_yield_pct": gross_yield,
                "estimated_slippage": est_slip,
                "gas_cost": gas_cost,
                "slippage_pct": round(est_slip + gas_cost, 4), # for backwards UI compatibility
                "net_apy_pct": round(net_apy, 4),
                "timestamp": int(time.time()),
                "is_external": False
            })
            
        # Solver 2: Flash_Quant (External)
        if quant_pick:
            gross_yield = quant_pick["current_yield_pct"] + round(random.uniform(0.1, 0.4), 4)
            est_slip = round(random.uniform(0.15, 0.30), 4) 
            gas_cost = round(random.uniform(0.05, 0.15), 4)
            net_apy = gross_yield - treasury_yield - est_slip - gas_cost
            bids.append({
                "solver": "Flash_Quant",
                "protocol_path": quant_pick["protocol"],
                "gross_yield_pct": round(gross_yield, 4),
                "estimated_slippage": est_slip,
                "gas_cost": gas_cost,
                "slippage_pct": round(est_slip + gas_cost, 4),
                "net_apy_pct": round(net_apy, 4),
                "timestamp": int(time.time()),
                "is_external": True
            })
            
        # Solver 3: Whale_Relay (External)
        if whale_pick:
            gross_yield = whale_pick["current_yield_pct"] + round(random.uniform(0.5, 1.0), 4)
            est_slip = round(random.uniform(0.50, 1.00), 4)
            gas_cost = round(random.uniform(0.20, 0.40), 4)
            net_apy = gross_yield - treasury_yield - est_slip - gas_cost
            bids.append({
                "solver": "Whale_Relay",
                "protocol_path": whale_pick["protocol"],
                "gross_yield_pct": round(gross_yield, 4),
                "estimated_slippage": est_slip,
                "gas_cost": gas_cost,
                "slippage_pct": round(est_slip + gas_cost, 4),
                "net_apy_pct": round(net_apy, 4),
                "timestamp": int(time.time()),
                "is_external": True
            })

        # Selection Logic: ZAIR Protocol automatically picks the path with Highest Net APY
        bids.sort(key=lambda x: x["net_apy_pct"], reverse=True)
        winning_bid = bids[0].copy()

        # Protocol Tax: 0.05% of transaction volume if an external solver is used
        if winning_bid["is_external"]:
            routing_tax_amount_usd = self.portfolio_usd * self.tax_rate
            winning_bid["net_apy_after_tax_pct"] = round(winning_bid["net_apy_pct"] - (self.tax_rate * 100), 4)
        else:
            routing_tax_amount_usd = 0
            winning_bid["net_apy_after_tax_pct"] = winning_bid["net_apy_pct"]
            
        winning_bid["routing_tax_pct"] = self.tax_rate * 100 if winning_bid["is_external"] else 0
        
        # Log decision to Audit Ledger
        log_decision(
            intent="SOLVER_AUCTION",
            ondo_apy=0.0,
            aave_borrow=0.0,
            spread=winning_bid["net_apy_pct"],
            action="SOLVER_WINNER",
            agent_signature=f"{winning_bid['solver']} won. Gas: {winning_bid['gas_cost']}%, Slip: {winning_bid['estimated_slippage']}%. Tax: ${routing_tax_amount_usd:,.2f}"
        )
        
        return {
            "auction_id": f"auc-{int(time.time())}",
            "bids": bids,
            "winner": winning_bid,
            "routing_tax_pct": winning_bid["routing_tax_pct"],
            "tax_usd_daily": routing_tax_amount_usd,
            "treasury_benchmark": treasury_yield
        }
