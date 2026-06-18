"""Persistence: SQLite via SQLModel. Order log + PnL ledger."""

from __future__ import annotations

import time
from typing import List, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=time.time, index=True)
    market_id: int = Field(index=True)
    token_id: str = Field(index=True)
    side: str
    order_type: str
    amount_usdc: float
    price: Optional[float] = None
    status: str
    order_id: Optional[str] = None
    reason: str = ""


class PnL(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=time.time, index=True)
    market_id: int
    realized_usdc: float


def make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)


def log_order(engine, **kwargs) -> None:
    with Session(engine) as s:
        s.add(Order(**kwargs))
        s.commit()


def recent_orders(engine, limit: int = 50) -> List[Order]:
    with Session(engine) as s:
        stmt = select(Order).order_by(Order.ts.desc()).limit(limit)
        return list(s.exec(stmt))
