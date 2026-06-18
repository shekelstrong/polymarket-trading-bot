"""Mean reversion: if the price has drifted > 2 std-dev from the rolling mean, fade it."""

from __future__ import annotations

from collections import deque
import math
from typing import Deque, List, Optional

from .base import Signal, Strategy


class MeanRevert(Strategy):
    name = "mean-revert"

    def __init__(self, window: int = 60, z_threshold: float = 2.0) -> None:
        self.window = window
        self.z_threshold = z_threshold
        self._prices: dict[str, Deque[float]] = {}

    def evaluate(
        self,
        *,
        market: dict,
        book: dict,
        last_trade_price: Optional[float],
    ) -> List[Signal]:
        if last_trade_price is None:
            return []
        token_id = book.get("asset_id") or market.get("clobTokenIds", [None])[0]
        if not token_id:
            return []
        dq = self._prices.setdefault(token_id, deque(maxlen=self.window))
        dq.append(last_trade_price)
        if len(dq) < self.window:
            return []
        mean = sum(dq) / len(dq)
        var = sum((p - mean) ** 2 for p in dq) / len(dq)
        std = math.sqrt(var) or 1e-9
        z = (dq[-1] - mean) / std
        if abs(z) < self.z_threshold:
            return []
        side = "SELL" if z > 0 else "BUY"  # fade the move
        return [
            Signal(
                market_id=int(market["id"]),
                market_question=market.get("question", ""),
                token_id=token_id,
                side=side,
                amount=3.0,
                order_type="FOK",
                tick_size="0.01",
                neg_risk=bool(market.get("negRisk", False)),
                reason=f"mean-revert z={z:+.2f} mean={mean:.3f}",
                confidence=min(1.0, abs(z) / (self.z_threshold * 2)),
            )
        ]
