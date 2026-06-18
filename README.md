# polymarket-trading-bot

Autonomous trading bot for [Polymarket](https://polymarket.com) prediction markets.

Two ways to run it:

1. **Bot mode** (default): one strategy runs against one wallet. Use this to put your own money to work.
2. **Backend mode** (`--serve`): exposes a small FastAPI that the [Polybet Mini App](../polymarket-miniapp) hits to place trades on behalf of authenticated Telegram users. This is the production wiring.

## What it does

- Streams live markets from `gamma-api.polymarket.com`.
- Maintains an in-memory order-book view per token via `clob.polymarket.com`.
- Runs a pluggable strategy (`momentum`, `mean-revert`, `news-edge`, or a custom subclass).
- Submits and cancels orders via `py-clob-client` (L2 authenticated, L3 if you have a funder).
- Optional RAG: feeds recent news (NewsAPI / RSS / Google News) into a vector store, and asks an LLM whether the consensus shifts a market.
- Persistent SQLite log of all orders and PnL.

## Stack

- Python 3.11+
- `py-clob-client`, `py-order-utils` (Polygon mainnet, chain id 137)
- `httpx` for the Gamma API
- `langchain` + `chromadb` for the RAG strategy (optional)
- `fastapi` + `uvicorn` for the backend mode
- `python-dotenv` for config
- `typer` for the CLI

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in your POLYGON_WALLET_PRIVATE_KEY
```

## Run as bot

```bash
python -m polybot --strategy momentum --budget 100
```

You will see a live log of markets scanned, signals, orders placed, and PnL updates.

## Run as backend (for the Mini App)

```bash
python -m polybot --serve --host 0.0.0.0 --port 8080
```

Endpoints:

```
GET  /healthz
GET  /markets/trending?limit=25
GET  /markets/orderbook/{token_id}
POST /trades              (JSON: see src/polybot/schemas.py)
POST /auth/telegram       (validates Telegram WebApp initData)
```

## Strategies

- `momentum`: if the last N trades moved the price up > X% on > Y volume, buy YES.
- `mean-revert`: if the price has drifted > Z standard deviations from the 1h VWAP, fade it.
- `news-edge`: when a new article clusters near a market's question, ask an LLM "is this market mispriced?" and trade if so.

Implement your own by subclassing `polybot.strategies.base.Strategy` and returning a list of `Signal` objects.

## Wallet

You need a Polygon wallet funded with USDC.e (bridged USDC). Approve the CLOB exchange contract to spend your USDC (the bot does this on first run, see `polybot.wallet.approvals`).

## Safety

- This bot trades real money.
- Default `--max-position` is $5, default `--max-daily-loss` is $25.
- Always start with a paper-trading wallet on Polygon Amoy testnet first (`POLYBOT_CHAIN_ID=80002`).

## License

MIT
