"""Pydantic schemas shared between the bot and the FastAPI backend."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Market(BaseModel):
    id: int
    question: str
    slug: Optional[str] = None
    description: Optional[str] = None
    endDate: Optional[str] = None
    image: Optional[str] = None
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    outcomes: List[str] = Field(default_factory=lambda: ["Yes", "No"])
    outcomePrices: List[str] = Field(default_factory=lambda: ["0.5", "0.5"])
    clobTokenIds: List[str] = Field(default_factory=list)
    acceptingOrders: bool = True
    negRisk: bool = False


class OrderBookLevel(BaseModel):
    price: str
    size: str


class OrderBook(BaseModel):
    market: str
    asset_id: str
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    midpoint: Optional[str] = None


TickSize = Literal["0.001", "0.01", "0.1"]
OrderType = Literal["GTC", "FOK", "GTD"]
Side = Literal["BUY", "SELL"]


class TradeRequest(BaseModel):
    tokenId: str
    side: Side
    outcome: Literal["YES", "NO"] = "YES"
    price: Optional[float] = Field(default=None, ge=0, le=1, description="Required for LIMIT")
    size: Optional[float] = Field(default=None, gt=0, description="Shares for LIMIT")
    amount: Optional[float] = Field(default=None, gt=0, description="USDC for MARKET")
    orderType: OrderType = "GTC"
    tickSize: TickSize = "0.01"
    negRisk: bool = False

    def market_or_limit(self) -> str:
        return "MARKET" if self.amount is not None else "LIMIT"


class TradeResponse(BaseModel):
    ok: bool
    orderId: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class TelegramAuthRequest(BaseModel):
    initData: str


class TelegramAuthResponse(BaseModel):
    ok: bool
    userId: Optional[int] = None
    username: Optional[str] = None
    error: Optional[str] = None
