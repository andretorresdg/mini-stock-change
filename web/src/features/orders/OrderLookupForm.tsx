import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiClientError, getOrder } from "../../api/client";
import type { OrderResponse, OrderStatus } from "../../api/types";
import EmptyState from "../../components/EmptyState";
import TwoColumnPage from "../../components/TwoColumnPage";
import { validateBrokerId, validateOrderId } from "./validation";

const STATUS_LABELS: Record<OrderStatus, string> = {
  OPEN: "Open",
  PARTIALLY_FILLED: "Partially filled",
  FILLED: "Filled",
  CANCELED: "Canceled",
  EXPIRED: "Expired",
};

const TERMINAL_STATUSES = new Set<OrderStatus>(["FILLED", "CANCELED", "EXPIRED"]);

// MVP uses conservative polling (5 s minimum interval).
// A production/live trading UI would likely use WebSocket or
// server-sent events.
const MIN_POLL_INTERVAL_MS = 5_000;

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

interface SubmittedPair {
  brokerId: string;
  orderId: string;
}

export default function OrderLookupForm() {
  const [brokerId, setBrokerId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [touchedBroker, setTouchedBroker] = useState(false);
  const [touchedOrder, setTouchedOrder] = useState(false);
  const [submittedPair, setSubmittedPair] = useState<SubmittedPair | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const brokerError = validateBrokerId(brokerId);
  const orderError = validateOrderId(orderId);
  const formValid = brokerError === null && orderError === null;

  const { data, isFetching, isError, error, dataUpdatedAt, refetch } = useQuery<
    OrderResponse,
    Error
  >({
    queryKey: ["order", submittedPair?.brokerId, submittedPair?.orderId],
    queryFn: () => getOrder(submittedPair!.brokerId, submittedPair!.orderId),
    enabled: submittedPair !== null,
    refetchInterval: (query) => {
      if (!autoRefresh) return false;
      const d = query.state.data;
      if (d !== undefined && TERMINAL_STATUSES.has(d.status)) return false;
      return MIN_POLL_INTERVAL_MS;
    },
    retry: 0,
    gcTime: 0,
  });

  const isTerminal = data !== undefined && TERMINAL_STATUSES.has(data.status);
  const lastUpdated =
    dataUpdatedAt > 0 ? new Date(dataUpdatedAt).toLocaleTimeString() : null;
  const hasSubmitted = submittedPair !== null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formValid || isFetching) return;
    const pair: SubmittedPair = { brokerId: brokerId.trim(), orderId: orderId.trim() };
    if (
      submittedPair !== null &&
      submittedPair.brokerId === pair.brokerId &&
      submittedPair.orderId === pair.orderId
    ) {
      void refetch();
    } else {
      setSubmittedPair(pair);
    }
  }

  function handleRefresh() {
    void refetch();
  }

  const leftColumn = (
    <>
      <p style={{ fontSize: "0.875rem", color: "#a0aec0", marginBottom: "1.25rem" }}>
        Enter the broker/user identifier and the order ID you received at submission. The
        order must belong to the specified broker/user.
      </p>
      <form onSubmit={handleSubmit} noValidate>
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
          disabled={!formValid || isFetching}
          style={{
            padding: "0.6rem 1.5rem",
            background: formValid && !isFetching ? "#3182ce" : "#2d3748",
            color: "#e2e8f0",
            border: "none",
            borderRadius: "4px",
            fontSize: "1rem",
            cursor: formValid && !isFetching ? "pointer" : "not-allowed",
          }}
        >
          {isFetching && data === undefined ? "Looking up…" : "Look up order"}
        </button>
      </form>

      {hasSubmitted && data !== undefined && (
        <div style={{ marginTop: "1.5rem" }}>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isFetching}
            style={{
              padding: "0.3rem 0.9rem",
              background: "#2d3748",
              color: "#e2e8f0",
              border: "1px solid #4a5568",
              borderRadius: "4px",
              cursor: isFetching ? "not-allowed" : "pointer",
              fontSize: "0.85rem",
              marginBottom: "0.75rem",
            }}
          >
            {isFetching ? "Refreshing…" : "Refresh now"}
          </button>

          <div>
            <label
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
                fontSize: "0.875rem",
                color: "#a0aec0",
                cursor: isTerminal ? "not-allowed" : "pointer",
              }}
            >
              <input
                type="checkbox"
                id="autoRefreshToggle"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                disabled={isTerminal}
              />
              Auto-refresh
            </label>
            <p
              style={{
                fontSize: "0.75rem",
                color: "#718096",
                marginTop: "0.25rem",
              }}
            >
              Auto-refresh checks every 5 seconds and stops when the order reaches a
              terminal status.
            </p>
          </div>
        </div>
      )}
    </>
  );

  let rightColumn: React.ReactNode;

  if (!hasSubmitted) {
    rightColumn = (
      <EmptyState>Enter a broker ID and order ID to view order status.</EmptyState>
    );
  } else if (isFetching && data === undefined) {
    rightColumn = (
      <p aria-live="polite" style={{ color: "#a0aec0" }}>
        Looking up order…
      </p>
    );
  } else if (isError && error !== null) {
    rightColumn = (
      <div
        role="alert"
        style={{
          background: "#742a2a",
          border: "1px solid #fc8181",
          borderRadius: "4px",
          padding: "0.75rem 1rem",
          color: "#fed7d7",
        }}
      >
        {error instanceof ApiClientError && error.apiError.status === 404
          ? "Order not found for this broker/user."
          : error instanceof ApiClientError
            ? error.apiError.message
            : "An unexpected error occurred."}
      </div>
    );
  } else if (data !== undefined) {
    rightColumn = (
      <section aria-labelledby="orderDetailsHeading">
        <h2 id="orderDetailsHeading" style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>
          Order details
        </h2>

        {lastUpdated !== null && (
          <p
            style={{ fontSize: "0.8rem", color: "#718096", marginBottom: "0.5rem" }}
            data-testid="last-updated"
          >
            Last updated at {lastUpdated}
          </p>
        )}

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
          <dd data-testid="detail-order-id">{data.order_id}</dd>

          <dt style={{ color: "#a0aec0" }}>Broker</dt>
          <dd data-testid="detail-broker-id">{data.broker_id}</dd>

          {data.client_order_id !== null && (
            <>
              <dt style={{ color: "#a0aec0" }}>Client order ID</dt>
              <dd data-testid="detail-client-order-id">{data.client_order_id}</dd>
            </>
          )}

          <dt style={{ color: "#a0aec0" }}>Document</dt>
          <dd data-testid="detail-document">{data.document_number}</dd>

          <dt style={{ color: "#a0aec0" }}>Side</dt>
          <dd data-testid="detail-side">{data.side}</dd>

          <dt style={{ color: "#a0aec0" }}>Symbol</dt>
          <dd data-testid="detail-symbol">{data.symbol}</dd>

          <dt style={{ color: "#a0aec0" }}>Unit price</dt>
          <dd data-testid="detail-price">{centsToDecimal(data.price)}</dd>

          <dt style={{ color: "#a0aec0" }}>Quantity</dt>
          <dd data-testid="detail-quantity">{data.quantity}</dd>

          <dt style={{ color: "#a0aec0" }}>Remaining</dt>
          <dd data-testid="detail-remaining">{data.remaining_quantity}</dd>

          <dt style={{ color: "#a0aec0" }}>Filled</dt>
          <dd data-testid="detail-filled">{data.filled_quantity}</dd>

          <dt style={{ color: "#a0aec0" }}>Status</dt>
          <dd data-testid="detail-status">
            <span aria-label={`Status: ${STATUS_LABELS[data.status]}`}>
              {STATUS_LABELS[data.status]}
            </span>
          </dd>

          <dt style={{ color: "#a0aec0" }}>Valid until</dt>
          <dd data-testid="detail-valid-until">
            {data.valid_until ?? "No expiration (GTC)"}
          </dd>
        </dl>

        {data.trades.length === 0 ? (
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
              {data.trades.map((t) => (
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
    );
  } else {
    rightColumn = null;
  }

  return <TwoColumnPage left={leftColumn} right={rightColumn} />;
}
