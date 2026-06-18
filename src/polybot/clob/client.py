"""Thin async wrapper around the synchronous py_clob_client.

We keep the official SDK (it owns the order-building EIP-712 signing) and
just give the rest of our code an async-friendly surface.
"""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    BalanceAllowanceParams,
    OpenOrderParams,
    OrderType as SdkOrderType,
)
from py_order_utils.builders import OrderBuilder  # noqa: F401  (re-exported)
from py_order_utils.signer import Signer  # noqa: F401

from ..logging_utils import get_logger
from ..schemas import OrderBook, OrderBookLevel, TradeRequest, TradeResponse
from .orders import build_signed_order

log = get_logger(__name__)


# Map our API types to the SDK enums without leaking the SDK import.
_SIDE_BUY = "BUY"
_ORDER_TYPE_MAP = {
    "GTC": SdkOrderType.GTC,
    "FOK": SdkOrderType.FOK,
    "GTD": SdkOrderType.GTD,
}


class ClobWrapper:
    """Owns a single ClobClient. Construct once at startup."""

    def __init__(
        self,
        host: str,
        chain_id: int,
        private_key: Optional[str],
        funder: Optional[str] = None,
        signature_type: int = 0,
    ) -> None:
        self._host = host
        # Level 0 (read-only) when no key is provided.
        if private_key:
            self._client = ClobClient(
                host,
                key=private_key,
                chain_id=chain_id,
                signature_type=signature_type,
                funder=funder,
            )
            self._creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(self._creds)
        else:
            self._client = ClobClient(host, chain_id=chain_id)
            self._creds = None
        log.info("clob client ready host=%s chain_id=%s", host, chain_id)

    # ---------- READ ----------
    async def get_order_book(self, token_id: str) -> OrderBook:
        book = await asyncio.to_thread(self._client.get_order_book, token_id)
        return OrderBook(
            market=book.market,
            asset_id=book.asset_id,
            bids=[OrderBookLevel(price=b.price, size=b.size) for b in book.bids],
            asks=[OrderBookLevel(price=a.price, size=a.size) for a in book.asks],
            midpoint=await asyncio.to_thread(self._client.get_midpoint, token_id),
        )

    async def get_prices(self, token_ids: List[str]) -> List[dict]:
        return await asyncio.to_thread(self._client.get_prices, token_ids)

    async def get_last_trade_price(self, token_id: str) -> Optional[float]:
        try:
            v = await asyncio.to_thread(self._client.get_last_trade_price, token_id)
            return float(v) if v is not None else None
        except Exception as e:
            log.warning("last_trade_price failed: %s", e)
            return None

    async def get_balance_allowance(self) -> Any:
        return await asyncio.to_thread(
            self._client.get_balance_allowance,
            BalanceAllowanceParams(asset_type="COLLATERAL"),
        )

    # ---------- WRITE ----------
    async def place_trade(self, req: TradeRequest) -> TradeResponse:
        """Submit a signed order, MARKET or LIMIT."""
        try:
            sdk_type = _ORDER_TYPE_MAP[req.orderType]
        except KeyError as e:
            return TradeResponse(ok=False, error=f"bad orderType: {e}")

        # Build the order via our own helper so we control the EIP-712 domain.
        signed = build_signed_order(
            client=self._client,
            req=req,
        )
        # Submit
        try:
            resp = await asyncio.to_thread(
                self._client.post_order, signed, sdk_type
            )
        except Exception as e:
            log.exception("post_order failed")
            return TradeResponse(ok=False, error=str(e))
        return TradeResponse(
            ok=True,
            orderId=(resp or {}).get("id") if isinstance(resp, dict) else None,
            status=(resp or {}).get("status") if isinstance(resp, dict) else "submitted",
        )

    async def cancel_all(self) -> dict:
        return await asyncio.to_thread(self._client.cancel_all)

    async def cancel_orders(self, ids: List[str]) -> dict:
        return await asyncio.to_thread(self._client.cancel_orders, ids)

    async def get_open_orders(self) -> Any:
        return await asyncio.to_thread(self._client.get_orders, OpenOrderParams())
