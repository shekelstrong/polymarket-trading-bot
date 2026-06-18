"""Tests run with `pytest`. Focus on the parts that don't need real money."""

from __future__ import annotations

from types import SimpleNamespace

from polybot.risk import RiskManager
from polybot.schemas import TradeRequest
from polybot.strategies.base import Signal
from polybot.strategies.mean_revert import MeanRevert
from polybot.strategies.momentum import Momentum


def test_momentum_emits_signal_after_window_filled():
    s = Momentum(window=5, threshold=0.01)
    book = SimpleNamespace(
        asset_id="0xabc",
        asks=[SimpleNamespace(price="0.55", size="10")],
    )
    out: list = []
    for p in [0.10, 0.10, 0.10, 0.10, 0.20]:
        out = s.evaluate(
            market={"id": 1, "question": "Q?", "negRisk": False},
            book=book.__dict__,
            last_trade_price=p,
        )
    assert out, "expected momentum signal after 100% move"
    assert out[0].side == "BUY"
    assert out[0].amount > 0


def test_mean_revert_is_quiet_when_within_threshold():
    s = MeanRevert(window=10, z_threshold=2.0)
    book = SimpleNamespace(asset_id="0xabc", asks=[SimpleNamespace(price="0.5", size="1")])
    out: list = []
    for p in [0.5] * 12:
        out = s.evaluate(
            market={"id": 1, "question": "Q?"},
            book=book.__dict__,
            last_trade_price=p,
        )
    assert out == []


def test_risk_manager_blocks_when_daily_loss_hit():
    rm = RiskManager(budget_usd=100, max_position_usd=5, max_daily_loss_usd=10)
    rm.state.realized_pnl_usd = -10.0
    sig = Signal(
        market_id=1,
        market_question="Q",
        token_id="0x",
        side="BUY",
        amount=2.0,
    )
    assert rm.approve(sig) is None


def test_risk_manager_caps_to_max_position():
    rm = RiskManager(budget_usd=100, max_position_usd=3, max_daily_loss_usd=10)
    sig = Signal(
        market_id=1,
        market_question="Q",
        token_id="0x",
        side="BUY",
        amount=10.0,
    )
    req = rm.approve(sig)
    assert req is not None
    assert req.amount == 3.0  # capped
