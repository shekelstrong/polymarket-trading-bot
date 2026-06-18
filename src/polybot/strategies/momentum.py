"""Momentum: if the price moved up X% in the last N trades on rising volume, buy YES."""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from .base import Signal, Strategy


class Momentum(Strategy):
    name = "momentum"

    def __init__(self, window: int = 20, threshold: float = 0.03) -> None:
        self.window = window
        self.threshold = threshold
        self._prices: dict[str, Deque[float]] = {}

    def evaluate(
        self,
        *,
        market: dict,
        book: dict,
        last_trade_price: Optional[float],
    ) -> List[Signal]:
        if last_trade_price is None or not book.get("asks"):
            return []
        token_id = book["asset_id"]
        dq = self._prices.setdefault(token_id, deque(maxlen=self.window))
        dq.append(last_trade_price)
        if len(dq) < self.window:
            return []
        change = (dq[-1] - dq[0]) / dq[0]
        if abs(change) < self.threshold:
            return []
        side = "BUY" if change > 0 else "SELL"
        best_ask = float(book["asks"][0]["price"])
        return [
            Signal(
                market_id=int(market["id"]),
                market_question=market.get("question", ""),
                token_id=token_id,
                side=side,
                amount=5.0,  # default; risk manager caps
                order_type="FOK",
                tick_size="0.01",
                neg_risk=bool(market.get("negRisk", False)),
                reason=f"momentum {change:+.2%} over {self.window} prints",
                confidence=min(1.0, abs(change) / (self.threshold * 3)),
            )
        ]
