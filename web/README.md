# mini-exchange web

A React + TypeScript + Vite MVP user interface for the [mini-exchange](../README.md) in-memory order book backend.

## Pages

### Submit Order (`/submit-order`)

Submit a limit order to the exchange. The form sends:

| Field | Description |
|-------|-------------|
| Broker / username | Your broker identifier |
| Document number | Your identification document number |
| Side | `BID` (buy) or `ASK` (sell) |
| Stock symbol | 1–4 letters, normalized to uppercase (e.g. `AAPL`) |
| Unit price | Decimal string (e.g. `150.00`), converted to integer cents (`15000`) before sending |
| Quantity | Positive whole number |
| Order validity | How long the order stays active: 15 min / 1 h / 4 h / 1 day |
| Client order ID *(optional)* | Your own reference key — enables idempotent retries |

After submitting, the exchange returns an **Order ID**.
**Save this Order ID** — you will need it to check the order status later.

### Order Status (`/status`)

Look up the current status of a previously submitted order.

Required fields:

| Field | Description |
|-------|-------------|
| Broker / username | Must be the broker/user who submitted the order |
| Order ID | The ID returned by the exchange at submission |

Displayed information: order ID, broker, document number, side, symbol, unit price (formatted as decimal), quantity, remaining quantity, filled quantity, status, valid-until, and any executed trades.

#### Auto-refresh

- Off by default.
- When enabled, polls every **5 seconds**.
- Stops automatically when the order reaches a terminal status (`FILLED`, `CANCELED`, `EXPIRED`).
- This MVP uses HTTP polling. A production UI would use WebSocket or server-sent events for lower latency and reduced server load.

## Getting Started

### Install dependencies

```bash
npm install
```

### Run the dev server

```bash
npm run dev
```

The app is served at `http://localhost:5173` by default.

### Configure the API base URL

The frontend calls `http://localhost:8000` by default.

Set `VITE_API_BASE_URL` to point to a different backend:

```bash
VITE_API_BASE_URL=https://api.example.com npm run dev
```

You can also create a `.env.local` file in this directory:

```
VITE_API_BASE_URL=https://api.example.com
```

## Development

### Run tests

```bash
npm test
```

### Run tests with coverage

```bash
npm run test:coverage
```

Coverage must remain at 100%.

### Lint

```bash
npm run lint
```

### Type-check

```bash
npm run typecheck
```

### Build for production

```bash
npm run build
```

## Tech Stack

| Tool | Purpose |
|------|---------|
| React 19 | UI framework |
| TypeScript | Static type checking |
| Vite | Build tool and dev server |
| React Router v7 | Client-side routing |
| TanStack Query v5 | Order status polling and cache |
| Vitest | Unit and component testing |
| React Testing Library | Component test utilities |
| ESLint | Linting |
