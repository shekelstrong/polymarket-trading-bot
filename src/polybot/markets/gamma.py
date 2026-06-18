"""Tiny async client for the Polymarket Gamma public API.

Used to enumerate markets and events. No auth, no signing, no money.
"""

from __future__ import annotations

from typing import Any, List, Optional

import httpx

from .schemas import Market


class GammaClient:
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com", timeout: float = 15.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GammaClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def get_markets(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
        order: Optional[str] = "volume",
        ascending: bool = False,
        tag_slug: Optional[str] = None,
    ) -> List[Market]:
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if order:
            params["order"] = order
            params["ascending"] = str(ascending).lower()
        if tag_slug:
            params["tag_slug"] = tag_slug

        r = await self._client.get("/markets", params=params)
        r.raise_for_status()
        out: List[Market] = []
        for raw in r.json():
            try:
                out.append(self._to_market(raw))
            except Exception:
                # Some markets have malformed lists; skip but keep going.
                continue
        return out

    @staticmethod
    def _to_market(raw: dict) -> Market:
        # outcomePrices and clobTokenIds come as JSON-encoded strings
        import json

        def _as_list(value, default):
            if value is None:
                return default
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return default
            return default

        outcomes = _as_list(raw.get("outcomes"), ["Yes", "No"])
        prices = _as_list(raw.get("outcomePrices"), ["0.5", "0.5"])
        token_ids = _as_list(raw.get("clobTokenIds"), [])
        return Market(
            id=int(raw["id"]),
            question=raw.get("question") or "",
            slug=raw.get("slug"),
            description=raw.get("description"),
            endDate=raw.get("endDate"),
            image=raw.get("image"),
            volume=float(raw.get("volumeNum") or raw.get("volume") or 0) or None,
            liquidity=float(raw.get("liquidityNum") or raw.get("liquidity") or 0) or None,
            outcomes=outcomes or ["Yes", "No"],
            outcomePrices=[str(p) for p in (prices or ["0.5", "0.5"])],
            clobTokenIds=[str(t) for t in (token_ids or [])],
            acceptingOrders=bool(raw.get("acceptingOrders", True)),
            negRisk=bool(raw.get("negRisk", False)),
        )
