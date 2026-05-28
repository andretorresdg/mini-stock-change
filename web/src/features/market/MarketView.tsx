import { useState } from "react";
import { ApiClientError, getBookSnapshot, getMarketTrades } from "../../api/client";
import type { BookSnapshotResponse, MarketTradesResponse } from "../../api/types";
import { sanitizeSymbolInput, validateSymbol } from "../orders/validation";

// MVP uses explicit refresh for market data.
// Live exchanges would usually push updates through
// WebSocket or streaming feeds.

type LoadStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; book: BookSnapshotResponse; trades: MarketTradesResponse }
  | { kind: "error"; message: string };

function formatCents(cents: number): string {
  return (cents / 100).toFixed(2);
}

const fieldStyle = { marginBottom: "1rem" };

const labelStyle = {
  display: "block",
  marginBottom: "0.375rem",
  fontSize: "0.875rem",
  color: "#a0aec0",
} as const;

const inputStyle = {
  background: "#2d3748",
  border: "1px solid #4a5568",
  borderRadius: "4px",
  color: "#e2e8f0",
  padding: "0.5rem 0.75rem",
  fontSize: "0.875rem",
  width: "100%",
  boxSizing: "border-box" as const,
};

const thStyle = {
  textAlign: "left" as const,
  padding: "0.4rem 0.75rem",
  fontSize: "0.8rem",
  color: "#a0aec0",
  borderBottom: "1px solid #2d3748",
};

const tdStyle = {
  padding: "0.4rem 0.75rem",
  fontSize: "0.875rem",
  color: "#e2e8f0",
};

export default function MarketView() {
  const [symbolInput, setSymbolInput] = useState("");
  const [depthInput, setDepthInput] = useState("10");
  const [limitInput, setLimitInput] = useState("20");
  const [loadStatus, setLoadStatus] = useState<LoadStatus>({ kind: "idle" });

  const symbolError = validateSymbol(symbolInput);
  const isSymbolValid = symbolInput.length > 0 && symbolError === null;
  const hasData = loadStatus.kind === "success";

  async function handleLoad(): Promise<void> {
    setLoadStatus({ kind: "loading" });
    try {
      const parsedDepth = parseInt(depthInput, 10);
      const parsedLimit = parseInt(limitInput, 10);
      const depth = Math.max(1, isFinite(parsedDepth) ? parsedDepth : 10);
      const limit = Math.max(1, isFinite(parsedLimit) ? parsedLimit : 20);
      const [book, trades] = await Promise.all([
        getBookSnapshot(symbolInput, depth),
        getMarketTrades(symbolInput, limit),
      ]);
      setLoadStatus({ kind: "success", book, trades });
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.apiError.message
          : "Failed to load market data";
      setLoadStatus({ kind: "error", message });
    }
  }

  return (
    <div>
      <h2>Market Data</h2>
      <p style={{ fontSize: "0.875rem", color: "#a0aec0", marginBottom: "1.5rem" }}>
        Current in-memory market state. Restarting the server resets the book
        and trades.
      </p>

      <div style={{ maxWidth: "26rem" }}>
        <div style={fieldStyle}>
          <label htmlFor="marketSymbol" style={labelStyle}>
            Symbol
          </label>
          <input
            id="marketSymbol"
            type="text"
            value={symbolInput}
            onChange={(e) => setSymbolInput(sanitizeSymbolInput(e.target.value))}
            placeholder="e.g. AAPL"
            maxLength={4}
            style={inputStyle}
          />
        </div>

        <div style={fieldStyle}>
          <label htmlFor="marketDepth" style={labelStyle}>
            Book depth
          </label>
          <input
            id="marketDepth"
            type="number"
            value={depthInput}
            onChange={(e) => setDepthInput(e.target.value)}
            min={1}
            max={50}
            style={inputStyle}
          />
        </div>

        <div style={fieldStyle}>
          <label htmlFor="marketLimit" style={labelStyle}>
            Trade limit
          </label>
          <input
            id="marketLimit"
            type="number"
            value={limitInput}
            onChange={(e) => setLimitInput(e.target.value)}
            min={1}
            max={200}
            style={inputStyle}
          />
        </div>

        <button
          type="button"
          onClick={() => {
            void handleLoad();
          }}
          disabled={!isSymbolValid || loadStatus.kind === "loading"}
          style={{
            background: isSymbolValid ? "#3182ce" : "#2d3748",
            color: "#e2e8f0",
            border: "none",
            borderRadius: "4px",
            padding: "0.6rem 1.25rem",
            fontSize: "0.9rem",
            cursor: isSymbolValid ? "pointer" : "not-allowed",
            opacity: loadStatus.kind === "loading" ? 0.6 : 1,
          }}
        >
          {hasData ? "Refresh" : "Load market data"}
        </button>
      </div>

      {loadStatus.kind === "loading" && (
        <p aria-live="polite" style={{ color: "#a0aec0", marginTop: "1rem" }}>
          Loading…
        </p>
      )}

      {loadStatus.kind === "error" && (
        <p role="alert" style={{ color: "#fc8181", marginTop: "1rem" }}>
          Error: {loadStatus.message}
        </p>
      )}

      {loadStatus.kind === "success" && (
        <>
          <section style={{ marginTop: "2rem" }}>
            <h3>Bids</h3>
            {loadStatus.book.bids.length === 0 ? (
              <p style={{ color: "#a0aec0" }}>No bids</p>
            ) : (
              <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "28rem" }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Price</th>
                    <th style={thStyle}>Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {loadStatus.book.bids.map((lvl) => (
                    <tr key={lvl.price}>
                      <td style={tdStyle}>{formatCents(lvl.price)}</td>
                      <td style={tdStyle}>{lvl.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section style={{ marginTop: "2rem" }}>
            <h3>Asks</h3>
            {loadStatus.book.asks.length === 0 ? (
              <p style={{ color: "#a0aec0" }}>No asks</p>
            ) : (
              <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "28rem" }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Price</th>
                    <th style={thStyle}>Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {loadStatus.book.asks.map((lvl) => (
                    <tr key={lvl.price}>
                      <td style={tdStyle}>{formatCents(lvl.price)}</td>
                      <td style={tdStyle}>{lvl.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section style={{ marginTop: "2rem" }}>
            <h3>Recent Trades</h3>
            {loadStatus.trades.trades.length === 0 ? (
              <p style={{ color: "#a0aec0" }}>No trades</p>
            ) : (
              <table
                style={{ borderCollapse: "collapse", width: "100%", maxWidth: "44rem" }}
              >
                <thead>
                  <tr>
                    <th style={thStyle}>Trade ID</th>
                    <th style={thStyle}>Seq</th>
                    <th style={thStyle}>Symbol</th>
                    <th style={thStyle}>Price</th>
                    <th style={thStyle}>Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {loadStatus.trades.trades.map((t) => (
                    <tr key={t.trade_id}>
                      <td style={tdStyle}>{t.trade_id}</td>
                      <td style={tdStyle}>{t.sequence}</td>
                      <td style={tdStyle}>{t.symbol}</td>
                      <td style={tdStyle}>{formatCents(t.price)}</td>
                      <td style={tdStyle}>{t.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}
