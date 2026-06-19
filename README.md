# Polymarket Trading Bot

Autonomous trading bot + FastAPI backend for the [Polybet Mini App](../polymarket-miniapp).

- **Stack:** Python 3.11+ + `py-clob-client` + `py-order-utils` + FastAPI + SQLModel
- **Chain:** Polygon mainnet (137)
- **License:** MIT

## Two modes

| Mode | Command | What |
|---|---|---|
| **Bot** | `python -m polybot --strategy momentum` | Scans markets, runs strategy, places real orders |
| **Serve** | `python -m polybot --serve --port 8080` | FastAPI for the Mini App (multi-user) |

## Strategies

- **`momentum`** — if price moved >3% over last 20 prints, trade in direction
- **`mean-revert`** — fade moves >2σ from rolling mean
- **`news-edge`** — LLM + Google News RSS → ask GPT-4o-mini "is this market mispriced?" → trade

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill POLYGON_WALLET_PRIVATE_KEY
```

## Run locally (paper trade)

```bash
# Switch to Amoy testnet
export POLYBOT_CHAIN_ID=80002
# Run bot
python -m polybot --strategy mean-revert
```

## Deploy via CI/CD

Already wired. Push to `main` → GitHub Actions → SSH to VPS 108.165.164.85 → `docker compose up -d --build`.

## Endpoints (when `--serve`)

| Method | Path | What |
|---|---|---|
| `GET` | `/healthz` | Liveness |
| `GET` | `/markets/trending?limit=25` | Top markets from Gamma |
| `GET` | `/markets/orderbook/{token_id}` | CLOB order book |
| `POST` | `/trades` | Sign + post order (requires wallet key) |
| `POST` | `/auth/telegram` | Verify Telegram WebApp initData |

## Polygon addresses

| Contract | Address |
|---|---|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` |
| Neg-Risk CTF Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` |
| USDC.e (Polygon) | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` |
| CTF Token | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Safety

- **`max_position_usd`** cap (default $5) — caps per-trade notional
- **`max_daily_loss_usd`** cap (default $25) — bot stops after daily loss limit
- **Read-only by default** — if `POLYGON_WALLET_PRIVATE_KEY` is empty, `/trades` returns 503

## License

MIT
