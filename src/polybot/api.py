"""FastAPI backend: serves the Mini App."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .clob.client import ClobWrapper
from .config import get_settings
from .logging_utils import get_logger
from .markets.gamma import GammaClient
from .schemas import (
    Market,
    OrderBook,
    TelegramAuthRequest,
    TelegramAuthResponse,
    TradeRequest,
    TradeResponse,
)

log = get_logger(__name__)


def _verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app"""
    if not init_data or not bot_token:
        raise HTTPException(status_code=400, detail="missing initData or bot token")
    parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
    recv_hash = parsed.pop("hash", None)
    if not recv_hash:
        raise HTTPException(status_code=400, detail="missing hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hashlib.sha256(b"WebAppData" + bot_token.encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, recv_hash):
        raise HTTPException(status_code=403, detail="bad signature")
    auth_date = int(parsed.get("auth_date", "0"))
    if auth_date and time.time() - auth_date > 24 * 3600:
        raise HTTPException(status_code=401, detail="initData expired")
    user = json.loads(parsed["user"]) if "user" in parsed else {}
    return user


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Polybet API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.gamma = GammaClient(base_url=settings.gamma_api_url)
        app.state.clob = ClobWrapper(
            host=settings.clob_api_url,
            chain_id=settings.chain_id,
            private_key=settings.polygon_wallet_private_key,
            funder=settings.polygon_funder_address,
        )
        log.info("polybet api up; chain_id=%s", settings.chain_id)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await app.state.gamma.close()

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "chain_id": settings.chain_id}

    @app.get("/markets/trending", response_model=List[Market])
    async def trending(limit: int = 25, offset: int = 0):
        try:
            return await app.state.gamma.get_markets(
                limit=limit,
                offset=offset,
                active=True,
                closed=False,
                order="volume",
                ascending=False,
            )
        except Exception as e:
            log.exception("trending failed")
            raise HTTPException(status_code=502, detail=str(e))

    @app.get("/markets/orderbook/{token_id}", response_model=OrderBook)
    async def orderbook(token_id: str):
        try:
            return await app.state.clob.get_order_book(token_id)
        except Exception as e:
            log.exception("orderbook failed")
            raise HTTPException(status_code=502, detail=str(e))

    @app.post("/trades", response_model=TradeResponse)
    async def trades(req: TradeRequest):
        if not settings.polygon_wallet_private_key:
            # Public read-only mode: refuse to place trades
            raise HTTPException(
                status_code=503,
                detail="trading is disabled: POLYGON_WALLET_PRIVATE_KEY not configured",
            )
        return await app.state.clob.place_trade(req)

    @app.post("/auth/telegram", response_model=TelegramAuthResponse)
    async def auth_telegram(body: TelegramAuthRequest):
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=503, detail="telegram bot token not configured")
        try:
            user = _verify_telegram_init_data(body.initData, settings.telegram_bot_token)
        except HTTPException:
            raise
        except Exception as e:
            log.exception("telegram verify failed")
            raise HTTPException(status_code=400, detail=str(e))
        raw_id = user.get("id")
        return TelegramAuthResponse(
            ok=True,
            userId=int(raw_id) if raw_id is not None else None,
            username=user.get("username"),
        )

    return app
