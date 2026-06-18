"""Make a real HTTP call to the Gamma public API.

Run with: `pytest tests/test_gamma_live.py -m live --run-live`
"""

from __future__ import annotations


import pytest

from polybot.markets.gamma import GammaClient


pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_gamma_live_returns_markets():
    async with GammaClient() as g:
        markets = await g.get_markets(limit=5, active=True, closed=False, order="volume")
        assert markets, "expected at least one market from the live Gamma API"
        m = markets[0]
        assert m.question
        assert m.outcomePrices
