"""News-edge: ask an LLM whether the latest news shifts a market's probability.

This is the highest-effort strategy. To enable, set OPENAI_API_KEY and
NEWS_API_KEY (or wire up a custom news source in `_fetch_headlines`).
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from ..logging_utils import get_logger
from .base import Signal, Strategy

log = get_logger(__name__)

# Very small, well-known universe of tickers. Extend freely.
_KEYWORD_HINTS = {
    "trump": ["trump", "donald", "republican", "gop", "maga"],
    "biden": ["biden", "democrat", "white house"],
    "election": ["election", "vote", "ballot", "primary"],
    "ukraine": ["ukraine", "zelensky", "kyiv", "kremlin"],
    "israel": ["israel", "gaza", "netanyahu", "hamas"],
    "bitcoin": ["bitcoin", "btc", "crypto", "etf"],
    "fed": ["fed", "fomc", "powell", "rate cut", "rate hike"],
    "ai": ["openai", "anthropic", "gpt", "claude", "llm", "ai model"],
    "tesla": ["tesla", "musk", "tsla", "cybertruck"],
}


def _classify(question: str) -> List[str]:
    q = question.lower()
    out: List[str] = []
    for tag, kws in _KEYWORD_HINTS.items():
        if any(kw in q for kw in kws):
            out.append(tag)
    return out


def _parse_signal(text: str) -> Optional[tuple[str, float, str]]:
    """Parse a one-line response like 'YES 0.65 because…' or 'NO 0.40 because…'."""
    m = re.match(r"\s*(YES|NO)\s+(\d*\.\d+|\d+)\b\s*(.*)", text.strip(), re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    side = m.group(1).upper()
    conf = float(m.group(2))
    reason = m.group(3).strip()[:200]
    return side, conf, reason


class NewsEdge(Strategy):
    name = "news-edge"

    def __init__(self, max_daily_calls: int = 200) -> None:
        self.calls = 0
        self.max_daily_calls = max_daily_calls
        self._llm = None
        self._news = None
        if os.getenv("OPENAI_API_KEY"):
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                log.info("news-edge: OpenAI enabled")
            except Exception as e:
                log.warning("news-edge: OpenAI init failed: %s", e)

    def evaluate(
        self,
        *,
        market: dict,
        book: dict,
        last_trade_price: Optional[float],
    ) -> List[Signal]:
        if not self._llm or self.calls >= self.max_daily_calls:
            return []
        tags = _classify(market.get("question", ""))
        if not tags:
            return []
        token_id = book.get("asset_id") or market.get("clobTokenIds", [None])[0]
        if not token_id:
            return []
        headlines = self._fetch_headlines(tags)[:5]
        if not headlines:
            return []
        prompt = (
            f"Market: {market['question']}\n"
            f"Current YES price: {market.get('outcomePrices', ['?','?'])[0]}\n"
            "Recent news:\n - " + "\n - ".join(headlines) +
            "\n\nReply with EXACTLY one line: 'YES <probability 0-1> <short reason>' "
            "or 'NO <probability 0-1> <short reason>'. Be terse."
        )
        try:
            resp = self._llm.invoke(prompt)
            self.calls += 1
        except Exception as e:
            log.warning("LLM call failed: %s", e)
            return []
        parsed = _parse_signal(resp.content if hasattr(resp, "content") else str(resp))
        if parsed is None:
            return []
        side, conf, reason = parsed
        if conf < 0.55:
            return []
        return [
            Signal(
                market_id=int(market["id"]),
                market_question=market.get("question", ""),
                token_id=token_id,
                side="BUY" if side == "YES" else "SELL",
                amount=4.0,
                order_type="FOK",
                tick_size="0.01",
                neg_risk=bool(market.get("negRisk", False)),
                reason=f"news-edge: {reason[:120]}",
                confidence=conf,
            )
        ]

    def _fetch_headlines(self, tags: List[str]) -> List[str]:
        """Cheap placeholder: use a free RSS feed by tag.
        Replace with NewsAPI / GDELT for production."""
        import httpx
        import xml.etree.ElementTree as ET

        out: List[str] = []
        # Use Google News RSS — free, no key.
        q = "+OR+".join(tags[:3])
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            r = httpx.get(url, timeout=8.0)
            if r.status_code != 200:
                return out
            root = ET.fromstring(r.text)
            for item in root.iter("item")[:8]:
                title = (item.findtext("title") or "").strip()
                if title:
                    out.append(title)
        except Exception as e:
            log.debug("news fetch failed: %s", e)
        return out


def build(name: str) -> Strategy:
    # Local imports to avoid a hard dependency on the LLM stack for non-news strategies
    n = name.lower()
    if n in ("momentum", "mom"):
        from .momentum import Momentum as _M
        return _M()
    if n in ("mean-revert", "mr", "mean_revert"):
        from .mean_revert import MeanRevert as _MR
        return _MR()
    if n in ("news-edge", "news", "llm"):
        return NewsEdge()
    raise ValueError(f"unknown strategy: {name}")
