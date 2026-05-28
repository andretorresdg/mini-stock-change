# mini-exchange

A deterministic order book core for a mini stock exchange.

## Design Principles

- **Deterministic**: Given the same input sequence, the order book always
  produces the same output. No wall-clock time, randomness, or UUIDs.
- **Integer arithmetic**: Prices and quantities are positive integers. Floats
  are never used.
- **Pure domain logic**: No database, API, networking, concurrency, or
  persistence. This is the matching core only.

## Matching Rules

| Rule | Description |
|------|-------------|
| Price-time priority | Best price first, then FIFO within the same price |
| BUY price | The maximum price the buyer is willing to pay |
| SELL price | The minimum price the seller is willing to accept |
| Execution price | Always the **seller** order price |
| Partial fills | Supported; orders can be partially filled across multiple trades |
| FIFO | Within the same price level, older orders match first |

## Architecture

- **`OrderBook`** represents one symbol. It owns both sides (bids and asks)
  and performs deterministic matching.
- **`MatchingEngine`** routes orders to per-symbol `OrderBook` instances.
  Books are created lazily on first access.

## Quick Example

```python
from mini_exchange.orderbook import OrderBook, Side

book = OrderBook("AAPL")

# Seller posts an ask at price 1000
book.submit_limit_order(broker_id="seller1", side=Side.SELL, price=1000, quantity=1)

# Buyer submits a bid at price 2000 (willing to pay up to 2000)
report = book.submit_limit_order(broker_id="buyer1", side=Side.BUY, price=2000, quantity=1)

# The trade executes at the seller's price
assert len(report.trades) == 1
assert report.trades[0].price == 1000
```

## Frontend

A React + TypeScript MVP UI lives in [`web/`](web/README.md).
See [web/README.md](web/README.md) for setup, configuration, and development instructions.

## Development

Requires Python >= 3.12.

```bash
pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

