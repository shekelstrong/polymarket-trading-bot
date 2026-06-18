"""Strategy base class and the signal it produces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Signal:
    """A single buy/sell intent emitted by a strategy."""

    market_id: int
    market_question: str
    token_id: str
    side: str  # "BUY" or "SELL"
    price: Optional[float] = None  # for LIMIT
    size: Optional[float] = None  # shares for LIMIT
    amount: Optional[float] = None  # USDC for MARKET
    order_type: str = "FOK"  # default to fill-or-kill for safety
    tick_size: str = "0.01"
    neg_risk: bool = False
    reason: str = ""
    confidence: float = 1.0  # 0..1, used by the risk manager to size


class Strategy:
    """Implement `.evaluate(market, book, last_trade_price) -> List[Signal]`."""

    name: str = "base"

    def evaluate(
        self,
        *,
        market: dict,
        book: dict,
        last_trade_price: Optional[float],
    ) -> List[Signal]:
        return []


def safe_size_usd(amount: float, max_position_usd: float) -> float:
    """Cap the per-trade notional to `max_position_usd`."""
    return max(0.0, min(amount, max_position_usd))
