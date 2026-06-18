"""Build a signed order using py-clob-client's helpers.

We isolate the order-building code so the rest of the bot never has to
touch the EIP-712 details.
"""

from __future__ import annotations

from typing import Any

from py_clob_client.clob_types import (
    MarketOrderArgs,
    OrderArgs,
)
from py_clob_client.order_builder.constants import BUY, SELL

from ..schemas import TradeRequest


def build_signed_order(client: Any, req: TradeRequest) -> Any:
    """Return a signed order object ready for `client.post_order`.

    MARKET orders spend `amount` USDC. LIMIT orders rest `size` shares at `price`.
    """
    side_const = BUY if req.side == "BUY" else SELL
    if req.amount is not None:
        # Market order
        args = MarketOrderArgs(
            token_id=req.tokenId,
            amount=req.amount,
            side=side_const,
        )
        return client.create_market_order(args)
    # Limit order
    if req.price is None or req.size is None:
        raise ValueError("LIMIT order requires both price and size")
    args = OrderArgs(
        token_id=req.tokenId,
        price=req.price,
        size=req.size,
        side=side_const,
    )
    return client.create_order(
        args,
        # options dict is set via create_and_post_order; here we just sign.
        options=None,
    )
