"""Risk manager: caps per-trade, daily, and exposure."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..logging_utils import get_logger
from ..schemas import TradeRequest
from ..strategies.base import Signal

log = get_logger(__name__)


@dataclass
class RiskState:
    realized_pnl_usd: float = 0.0
    day_started_at: float = time.time()
    open_positions_usd: float = 0.0

    def reset_if_new_day(self) -> None:
        if time.time() - self.day_started_at > 24 * 3600:
            self.realized_pnl_usd = 0.0
            self.day_started_at = time.time()


class RiskManager:
    def __init__(
        self,
        *,
        budget_usd: float,
        max_position_usd: float,
        max_daily_loss_usd: float,
    ) -> None:
        self.budget = budget_usd
        self.max_position = max_position_usd
        self.max_daily_loss = max_daily_loss_usd
        self.state = RiskState()

    def approve(self, sig: Signal) -> TradeRequest | None:
        """Translate a Signal into a TradeRequest, or return None if blocked."""
        self.state.reset_if_new_day()
        if -self.state.realized_pnl_usd >= self.max_daily_loss:
            log.warning("daily loss limit hit, skipping signal: %s", sig.reason)
            return None
        notional = min(sig.amount or 0.0, self.max_position)
        if notional < 1.0:
            return None
        if self.state.open_positions_usd + notional > self.budget:
            log.warning(
                "budget exceeded (open=%.2f + new=%.2f > %.2f), skipping",
                self.state.open_positions_usd,
                notional,
                self.budget,
            )
            return None
        return TradeRequest(
            tokenId=sig.token_id,
            side=sig.side,  # type: ignore[arg-type]
            amount=notional,
            orderType=sig.order_type,  # type: ignore[arg-type]
            tickSize=sig.tick_size,  # type: ignore[arg-type]
            negRisk=sig.neg_risk,
        )
