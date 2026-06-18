"""Bot main loop: scan markets, run strategy, place trades via ClobWrapper."""

from __future__ import annotations

import asyncio

from .clob.client import ClobWrapper
from .config import get_settings
from .logging_utils import get_logger
from .markets.gamma import GammaClient
from .persistence import init_db, log_order, make_engine
from .risk import RiskManager
from .strategies.base import Strategy
from .strategies import news_edge

log = get_logger(__name__)


async def scan_once(
    gamma: GammaClient,
    clob: ClobWrapper,
    strategy: Strategy,
    risk: RiskManager,
    engine,
    *,
    limit: int = 50,
) -> int:
    """One full pass. Returns the number of orders submitted."""
    markets = await gamma.get_markets(limit=limit, active=True, closed=False, order="volume")
    placed = 0
    for m in markets:
        if not m.clobTokenIds:
            continue
        token_id = m.clobTokenIds[0]  # YES token
        try:
            book = await clob.get_order_book(token_id)
            last = await clob.get_last_trade_price(token_id)
        except Exception as e:
            log.debug("book fetch failed for %s: %s", m.slug, e)
            continue
        signals = strategy.evaluate(
            market=m.model_dump(),
            book=book.model_dump(),
            last_trade_price=last,
        )
        for sig in signals:
            req = risk.approve(sig)
            if req is None:
                continue
            resp = await clob.place_trade(req)
            log_order(
                engine,
                market_id=m.id,
                token_id=req.tokenId,
                side=req.side,
                order_type=req.orderType,
                amount_usdc=req.amount or 0.0,
                price=req.price,
                status=(resp.status or ("ok" if resp.ok else "err")),
                order_id=resp.orderId,
                reason=sig.reason,
            )
            log.info("placed: %s market=%s reason=%s", resp.status, m.slug, sig.reason)
            placed += 1
    return placed


async def run_bot(strategy_name: str, *, scan_interval: float = 15.0) -> None:
    settings = get_settings()
    engine = make_engine(settings.db_url)
    init_db(engine)
    gamma = GammaClient(base_url=settings.gamma_api_url)
    clob = ClobWrapper(
        host=settings.clob_api_url,
        chain_id=settings.chain_id,
        private_key=settings.polygon_wallet_private_key,
        funder=settings.polygon_funder_address,
    )
    strategy = news_edge.build(strategy_name)
    risk = RiskManager(
        budget_usd=settings.budget_usdc,
        max_position_usd=settings.max_position_usdc,
        max_daily_loss_usd=settings.max_daily_loss_usd,
    )
    log.info(
        "starting bot: strategy=%s budget=$%.2f max_pos=$%.2f max_loss=$%.2f",
        strategy.name,
        settings.budget_usdc,
        settings.max_position_usdc,
        settings.max_daily_loss_usd,
    )
    try:
        while True:
            try:
                n = await scan_once(gamma, clob, strategy, risk, engine)
                if n:
                    log.info("cycle: placed %d orders", n)
                else:
                    log.debug("cycle: no signals")
            except Exception as e:
                log.exception("scan failed: %s", e)
            await asyncio.sleep(scan_interval)
    finally:
        await gamma.close()
