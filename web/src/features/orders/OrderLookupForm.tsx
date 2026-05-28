import { useState } from "react";
import { ApiClientError, getOrder } from "../../api/client";
import type { OrderResponse, OrderStatus } from "../../api/types";
import { validateBrokerId, validateOrderId } from "./validation";

type LookupStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; order: OrderResponse }
  | { kind: "refreshing"; order: OrderResponse }
  | { kind: "error"; message: string };

const STATUS_LABELS: Record<OrderStatus, string> = {
  OPEN: "Open",
  PARTIALLY_FILLED: "Partially filled",
  FILLED: "Filled",
  CANCELED: "Canceled",
  EXPIRED: "Expired",
};

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "0.5rem 0.75rem",
  background: "#1a202c",
  border: "1px solid #4a5568",
  borderRadius: "4px",
  color: "#e2e8f0",
  fontSize: "1rem",
  marginTop: "0.25rem",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontWeight: 500,
  color: "#a0aec0",
  fontSize: "0.875rem",
};

const fieldStyle: React.CSSProperties = { marginBottom: "1.25rem" };

const errorStyle: React.CSSProperties = {
  color: "#fc8181",
  fontSize: "0.8rem",
  marginTop: "0.25rem",
  display: "block",
};

function centsToDecimal(cents: number): string {
  return (cents / 100).toFixed(2);
}

export default function OrderLookupForm() {
  const [brokerId, setBrokerId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [touchedBroker, setTouchedBroker] = useState(false);
  const [touchedOrder, setTouchedOrder] = useState(false);
  const [status, setStatus] = useState<LookupStatus>({ kind: "idle" });

  const brokerError = validateBrokerId(brokerId);
  const orderError = validateOrderId(orderId);
  const formValid = brokerError === null && orderError === null;
  const isLoading = status.kind === "loading" || status.kind === "refreshing";

  async function doLookup() {
    if (!formValid || isLoading) return;
    const prevOrder = status.kind === "success" ? status.order : undefined;
    setStatus(
      prevOrder !== undefined
        ? { kind: "refreshing", order: prevOrder }
        : { kind: "loading" },
    );
    try {
      const result = await getOrder(brokerId, orderId.trim());
      setStatus({ kind: "success", order: result });
    } catch (err) {
      if (err instanceof ApiClientError && err.apiError.status === 404) {
        setStatus({ kind: "error", message: "Order not found for this broker/user." });
      } else {
        const message =
          err instanceof ApiClientError
            ? err.apiError.message
            : "An unexpected error occurred.";
        setStatus({ kind: "error", message });
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await doLookup();
  }

  async function handleRefresh() {
    await doLookup();
  }

  const displayedOrder =
    status.kind === "success" || status.kind === "refreshing" ? status.order : null;

  return (
    <div>
      <form onSubmit={handleSubmit} noValidate>
        {/* Broker / username */}
        <div style={fieldStyle}>
          <label htmlFor="lookupBrokerId" style={labelStyle}>
            Broker / username
          </label>
          <input
            id="lookupBrokerId"
            type="text"
            autoComplete="off"
            value={brokerId}
            onChange={(e) => setBrokerId(e.target.value)}
            onBlur={() => setTouchedBroker(true)}
            aria-describedby={
              touchedBroker && brokerError ? "lookupBrokerIdError" : undefined
            }
            style={inputStyle}
          />
          {touchedBroker && brokerError && (
            <span id="lookupBrokerIdError" role="alert" style={errorStyle}>
              {brokerError}
            </span>
          )}
        </div>

        {/* Order ID */}
        <div style={fieldStyle}>
          <label htmlFor="lookupOrderId" style={labelStyle}>
            Order ID
          </label>
          <input
            id="lookupOrderId"
            type="text"
            autoComplete="off"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            onBlur={() => setTouchedOrder(true)}
            aria-describedby={
              touchedOrder && orderError ? "lookupOrderIdError" : undefined
            }
            style={inputStyle}
          />
          {touchedOrder && orderError && (
            <span id="lookupOrderIdError" role="alert" style={errorStyle}>
              {orderError}
            </span>
          )}
        </div>

        <button
          type="submit"
          disabled={!formValid || isLoading}
          style={{
            padding: "0.6rem 1.5rem",
            background: formValid && !isLoading ? "#3182ce" : "#2d3748",
            color: "#e2e8f0",
            border: "none",
            borderRadius: "4px",
            fontSize: "1rem",
            cursor: formValid && !isLoading ? "pointer" : "not-allowed",
          }}
        >
          {isLoading ? "Looking up…" : "Look up order"}
        </button>
      </form>

      {/* Error feedback */}
      {status.kind === "error" && (
        <div
          role="alert"
          style={{
            background: "#742a2a",
            border: "1px solid #fc8181",
            borderRadius: "4px",
            padding: "0.75rem 1rem",
            marginTop: "1rem",
            color: "#fed7d7",
          }}
        >
          {status.message}
        </div>
      )}

      {/* Order details */}
      {displayedOrder !== null && (
        <section
          aria-labelledby="orderDetailsHeading"
          style={{ marginTop: "1.5rem" }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "1rem",
              marginBottom: "1rem",
            }}
          >
            <h2 id="orderDetailsHeading" style={{ fontSize: "1.1rem" }}>
              Order details
            </h2>
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              style={{
                padding: "0.3rem 0.9rem",
                background: "#2d3748",
                color: "#e2e8f0",
                border: "1px solid #4a5568",
                borderRadius: "4px",
                cursor: isLoading ? "not-allowed" : "pointer",
                fontSize: "0.85rem",
              }}
            >
              {isLoading ? "Refreshing…" : "Refresh now"}
            </button>
          </div>

          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              gap: "0.4rem 1rem",
              marginBottom: "1.5rem",
              fontSize: "0.9rem",
            }}
          >
            <dt style={{ color: "#a0aec0" }}>Order ID</dt>
            <dd data-testid="detail-order-id">{displayedOrder.order_id}</dd>

            <dt style={{ color: "#a0aec0" }}>Broker</dt>
            <dd data-testid="detail-broker-id">{displayedOrder.broker_id}</dd>

            {displayedOrder.client_order_id !== null && (
              <>
                <dt style={{ color: "#a0aec0" }}>Client order ID</dt>
                <dd data-testid="detail-client-order-id">
                  {displayedOrder.client_order_id}
                </dd>
              </>
            )}

            <dt style={{ color: "#a0aec0" }}>Document</dt>
            <dd data-testid="detail-document">{displayedOrder.document_number}</dd>

            <dt style={{ color: "#a0aec0" }}>Side</dt>
            <dd data-testid="detail-side">{displayedOrder.side}</dd>

            <dt style={{ color: "#a0aec0" }}>Symbol</dt>
            <dd data-testid="detail-symbol">{displayedOrder.symbol}</dd>

            <dt style={{ color: "#a0aec0" }}>Unit price</dt>
            <dd data-testid="detail-price">{centsToDecimal(displayedOrder.price)}</dd>

            <dt style={{ color: "#a0aec0" }}>Quantity</dt>
            <dd data-testid="detail-quantity">{displayedOrder.quantity}</dd>

            <dt style={{ color: "#a0aec0" }}>Remaining</dt>
            <dd data-testid="detail-remaining">{displayedOrder.remaining_quantity}</dd>

            <dt style={{ color: "#a0aec0" }}>Filled</dt>
            <dd data-testid="detail-filled">{displayedOrder.filled_quantity}</dd>

            <dt style={{ color: "#a0aec0" }}>Status</dt>
            <dd data-testid="detail-status">
              <span aria-label={`Status: ${STATUS_LABELS[displayedOrder.status]}`}>
                {STATUS_LABELS[displayedOrder.status]}
              </span>
            </dd>

            <dt style={{ color: "#a0aec0" }}>Valid until</dt>
            <dd data-testid="detail-valid-until">{displayedOrder.valid_until}</dd>
          </dl>

          {/* Trades */}
          {displayedOrder.trades.length === 0 ? (
            <p style={{ color: "#a0aec0", fontSize: "0.9rem" }}>No trades yet.</p>
          ) : (
            <table
              aria-label="Trades"
              style={{ width: "100%", borderCollapse: "collapse" }}
            >
              <thead>
                <tr>
                  {["Trade ID", "Price", "Quantity", "Buyer", "Seller"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "0.4rem 0.6rem",
                        color: "#a0aec0",
                        borderBottom: "1px solid #2d3748",
                        fontSize: "0.8rem",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayedOrder.trades.map((t) => (
                  <tr key={t.trade_id}>
                    <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                      {t.trade_id}
                    </td>
                    <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                      {centsToDecimal(t.price)}
                    </td>
                    <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                      {t.quantity}
                    </td>
                    <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                      {t.buyer_broker_id}
                    </td>
                    <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                      {t.seller_broker_id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
