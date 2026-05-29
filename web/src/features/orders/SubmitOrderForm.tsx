import { useState } from "react";
import { ApiClientError, submitOrder } from "../../api/client";
import type { OrderResponse, OrderSide } from "../../api/types";
import Panel from "../../components/Panel";
import TwoColumnPage from "../../components/TwoColumnPage";
import {
  normalizePriceDisplay,
  PRICE_DOT_HINT,
  priceToCents,
  quantityToApiInteger,
  sanitizePriceInput,
  sanitizeQuantityInput,
  sanitizeSymbolInput,
  utcDateTimeLocalToIso,
  validateBrokerId,
  validateDocumentNumber,
  validateExpiration,
  validatePrice,
  validateQuantity,
  validateSymbol,
} from "./validation";

type ValidityMode = "GTC" | "EXPIRES";

const FORM_ID = "submit-order-form";

// The UI generates this idempotency key so users do not need to manage retry
// IDs manually. Broker API clients may still send their own client_order_id.
function generateClientOrderId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `cli-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function formatValidUntil(value: string | null): string {
  return value === null ? "No expiration (GTC)" : value;
}

interface FormState {
  brokerId: string;
  documentNumber: string;
  side: OrderSide;
  symbol: string;
  price: string;
  quantity: string;
  validityMode: ValidityMode;
  expiresAt: string;
}

interface FormErrors {
  brokerId: string | null;
  documentNumber: string | null;
  symbol: string | null;
  price: string | null;
  quantity: string | null;
  expiration: string | null;
}

type SubmitStatus =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "success"; order: OrderResponse }
  | { kind: "error"; message: string };

function validate(state: FormState): FormErrors {
  return {
    brokerId: validateBrokerId(state.brokerId),
    documentNumber: validateDocumentNumber(state.documentNumber),
    symbol: validateSymbol(state.symbol),
    price: validatePrice(state.price),
    quantity: validateQuantity(state.quantity),
    expiration:
      state.validityMode === "EXPIRES" ? validateExpiration(state.expiresAt) : null,
  };
}

function isValid(errors: FormErrors): boolean {
  return Object.values(errors).every((e) => e === null);
}

const INITIAL_FORM: FormState = {
  brokerId: "",
  documentNumber: "",
  side: "BID",
  symbol: "",
  price: "",
  quantity: "",
  validityMode: "GTC",
  expiresAt: "",
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

const buttonStyle = (enabled: boolean): React.CSSProperties => ({
  padding: "0.6rem 1.5rem",
  background: enabled ? "#3182ce" : "#2d3748",
  color: "#e2e8f0",
  border: "none",
  borderRadius: "4px",
  fontSize: "1rem",
  cursor: enabled ? "pointer" : "not-allowed",
});

interface SuccessPanelProps {
  order: OrderResponse;
  onReset: () => void;
}

function SuccessPanel({ order, onReset }: SuccessPanelProps) {
  return (
    <section aria-labelledby="successHeading" role="region">
      <h2 id="successHeading" style={{ color: "#68d391", marginBottom: "1rem" }}>
        Order submitted
      </h2>
      <p style={{ color: "#fbd38d", marginBottom: "1.5rem" }}>
        Save this order ID. You will need it to check the order status later.
      </p>
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "0.4rem 1rem",
          marginBottom: "1.5rem",
        }}
      >
        <dt style={{ color: "#a0aec0" }}>Order ID</dt>
        <dd data-testid="success-order-id">{order.order_id}</dd>
        <dt style={{ color: "#a0aec0" }}>Status</dt>
        <dd data-testid="success-status">{order.status}</dd>
        <dt style={{ color: "#a0aec0" }}>Validity</dt>
        <dd data-testid="success-validity">{formatValidUntil(order.valid_until)}</dd>
        <dt style={{ color: "#a0aec0" }}>Remaining</dt>
        <dd data-testid="success-remaining">{order.remaining_quantity}</dd>
        <dt style={{ color: "#a0aec0" }}>Filled</dt>
        <dd data-testid="success-filled">{order.filled_quantity}</dd>
        <dt style={{ color: "#a0aec0" }}>Trades</dt>
        <dd data-testid="success-trade-count">{order.trades.length}</dd>
      </dl>

      {order.trades.length > 0 && (
        <table
          aria-label="Trades"
          style={{ width: "100%", borderCollapse: "collapse", marginBottom: "1.5rem" }}
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
            {order.trades.map((t) => (
              <tr key={t.trade_id}>
                <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                  {t.trade_id}
                </td>
                <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}>
                  {(t.price / 100).toFixed(2)}
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

      <button
        type="button"
        onClick={onReset}
        style={{
          padding: "0.6rem 1.5rem",
          background: "#2d3748",
          color: "#e2e8f0",
          border: "1px solid #4a5568",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "1rem",
        }}
      >
        Submit another order
      </button>
    </section>
  );
}

export default function SubmitOrderForm() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof FormErrors, boolean>>>({});
  const [status, setStatus] = useState<SubmitStatus>({ kind: "idle" });

  const errors = validate(form);
  const formValid = isValid(errors);
  const isPending = status.kind === "pending";
  const isSuccess = status.kind === "success";

  function touch(field: keyof FormErrors) {
    setTouched((t) => ({ ...t, [field]: true }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formValid || isPending) return;
    setStatus({ kind: "pending" });
    try {
      const validUntil =
        form.validityMode === "GTC" ? null : utcDateTimeLocalToIso(form.expiresAt);
      const result = await submitOrder(form.brokerId, {
        client_order_id: generateClientOrderId(),
        document_number: form.documentNumber,
        side: form.side,
        valid_until: validUntil,
        symbol: form.symbol,
        price: priceToCents(form.price),
        quantity: quantityToApiInteger(form.quantity),
      });
      setStatus({ kind: "success", order: result });
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.apiError.message
          : "An unexpected error occurred.";
      setStatus({ kind: "error", message });
    }
  }

  function handleReset() {
    setForm(INITIAL_FORM);
    setTouched({});
    setStatus({ kind: "idle" });
  }

  const previewSide = form.side;
  const previewSymbol = form.symbol || "—";
  const previewPrice = form.price ? normalizePriceDisplay(form.price) || "—" : "—";
  const previewQuantity = form.quantity || "—";

  let notional = "—";
  if (!errors.price && !errors.quantity && form.price && form.quantity) {
    const cents = priceToCents(form.price);
    const qty = quantityToApiInteger(form.quantity);
    notional = `$${((cents * qty) / 100).toFixed(2)}`;
  }

  const leftColumn = (
    <form id={FORM_ID} onSubmit={handleSubmit} noValidate>
      <div style={fieldStyle}>
        <label htmlFor="brokerId" style={labelStyle}>
          Broker / username
        </label>
        <input
          id="brokerId"
          type="text"
          autoComplete="off"
          value={form.brokerId}
          onChange={(e) => setForm((f) => ({ ...f, brokerId: e.target.value }))}
          onBlur={() => touch("brokerId")}
          aria-describedby={touched.brokerId && errors.brokerId ? "brokerIdError" : undefined}
          style={inputStyle}
        />
        {touched.brokerId && errors.brokerId && (
          <span id="brokerIdError" role="alert" style={errorStyle}>
            {errors.brokerId}
          </span>
        )}
      </div>

      <div style={fieldStyle}>
        <label htmlFor="documentNumber" style={labelStyle}>
          Customer document number
        </label>
        <span
          id="documentNumberHelp"
          style={{ color: "#718096", fontSize: "0.8rem", display: "block" }}
        >
          Identifies the customer represented by the broker.
        </span>
        <input
          id="documentNumber"
          type="text"
          autoComplete="off"
          value={form.documentNumber}
          onChange={(e) => setForm((f) => ({ ...f, documentNumber: e.target.value }))}
          onBlur={() => touch("documentNumber")}
          aria-describedby={
            touched.documentNumber && errors.documentNumber
              ? "documentNumberHelp documentNumberError"
              : "documentNumberHelp"
          }
          style={inputStyle}
        />
        {touched.documentNumber && errors.documentNumber && (
          <span id="documentNumberError" role="alert" style={errorStyle}>
            {errors.documentNumber}
          </span>
        )}
      </div>

      <div style={fieldStyle} role="group" aria-labelledby="sideLabel">
        <span
          id="sideLabel"
          style={{ ...labelStyle, display: "block", marginBottom: "0.5rem" }}
        >
          Order side
        </span>
        <div style={{ display: "flex", gap: "1.5rem" }}>
          {(["BID", "ASK"] as OrderSide[]).map((s) => (
            <label
              key={s}
              style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer" }}
            >
              <input
                type="radio"
                name="side"
                value={s}
                checked={form.side === s}
                onChange={() => setForm((f) => ({ ...f, side: s }))}
              />
              {s}
            </label>
          ))}
        </div>
      </div>

      <div style={fieldStyle}>
        <label htmlFor="symbol" style={labelStyle}>
          Stock symbol
        </label>
        <input
          id="symbol"
          type="text"
          autoComplete="off"
          value={form.symbol}
          onChange={(e) => {
            const sanitized = sanitizeSymbolInput(e.target.value);
            setForm((f) => ({ ...f, symbol: sanitized }));
            touch("symbol");
          }}
          onBlur={() => touch("symbol")}
          aria-describedby={touched.symbol && errors.symbol ? "symbolError" : undefined}
          style={inputStyle}
        />
        {touched.symbol && errors.symbol && (
          <span id="symbolError" role="alert" style={errorStyle}>
            {errors.symbol}
          </span>
        )}
      </div>

      <div style={fieldStyle}>
        <label htmlFor="price" style={labelStyle}>
          Unit price (USD)
        </label>
        <span
          id="priceHelp"
          style={{ color: "#718096", fontSize: "0.8rem", display: "block" }}
        >
          {PRICE_DOT_HINT}
        </span>
        <input
          id="price"
          type="text"
          inputMode="decimal"
          autoComplete="off"
          placeholder="10.00"
          value={form.price}
          onChange={(e) => {
            const sanitized = sanitizePriceInput(e.target.value);
            setForm((f) => ({ ...f, price: sanitized }));
            touch("price");
          }}
          onBlur={() => {
            const normalized = normalizePriceDisplay(form.price);
            setForm((f) => ({ ...f, price: normalized }));
            touch("price");
          }}
          aria-describedby={
            touched.price && errors.price ? "priceHelp priceError" : "priceHelp"
          }
          style={inputStyle}
        />
        {touched.price && errors.price && (
          <span id="priceError" role="alert" style={errorStyle}>
            {errors.price}
          </span>
        )}
      </div>

      <div style={fieldStyle}>
        <label htmlFor="quantity" style={labelStyle}>
          Quantity
        </label>
        <input
          id="quantity"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={form.quantity}
          onChange={(e) => {
            const sanitized = sanitizeQuantityInput(e.target.value);
            setForm((f) => ({ ...f, quantity: sanitized }));
            touch("quantity");
          }}
          onBlur={() => touch("quantity")}
          aria-describedby={touched.quantity && errors.quantity ? "quantityError" : undefined}
          style={inputStyle}
        />
        {touched.quantity && errors.quantity && (
          <span id="quantityError" role="alert" style={errorStyle}>
            {errors.quantity}
          </span>
        )}
      </div>

      <div style={fieldStyle}>
        <label htmlFor="validityMode" style={labelStyle}>
          Order validity
        </label>
        <select
          id="validityMode"
          value={form.validityMode}
          onChange={(e) =>
            setForm((f) => ({ ...f, validityMode: e.target.value as ValidityMode }))
          }
          style={inputStyle}
        >
          <option value="GTC">No expiration (GTC)</option>
          <option value="EXPIRES">Expires at specific UTC date/time</option>
        </select>
      </div>

      {form.validityMode === "EXPIRES" && (
        <div style={fieldStyle}>
          <label htmlFor="expiresAt" style={labelStyle}>
            Expiration date and time (UTC)
          </label>
          <span
            id="expiresAtHelp"
            style={{ color: "#718096", fontSize: "0.8rem", display: "block" }}
          >
            Times are interpreted as UTC.
          </span>
          <input
            id="expiresAt"
            type="datetime-local"
            value={form.expiresAt}
            onChange={(e) => {
              const value = e.target.value;
              setForm((f) => ({ ...f, expiresAt: value }));
              touch("expiration");
            }}
            aria-describedby={
              touched.expiration && errors.expiration
                ? "expiresAtHelp expiresAtError"
                : "expiresAtHelp"
            }
            style={inputStyle}
          />
          {touched.expiration && errors.expiration && (
            <span id="expiresAtError" role="alert" style={errorStyle}>
              {errors.expiration}
            </span>
          )}
        </div>
      )}
    </form>
  );

  const rightColumn = isSuccess ? (
    <SuccessPanel order={status.order} onReset={handleReset} />
  ) : (
    <>
      <Panel title="Order preview" titleId="previewHeading">
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "0.25rem 1rem",
            fontSize: "0.9rem",
          }}
        >
          <dt style={{ color: "#718096" }}>Side</dt>
          <dd data-testid="preview-side">{previewSide}</dd>
          <dt style={{ color: "#718096" }}>Symbol</dt>
          <dd data-testid="preview-symbol">{previewSymbol}</dd>
          <dt style={{ color: "#718096" }}>Price</dt>
          <dd data-testid="preview-price">{previewPrice}</dd>
          <dt style={{ color: "#718096" }}>Quantity</dt>
          <dd data-testid="preview-quantity">{previewQuantity}</dd>
          <dt style={{ color: "#718096" }}>Estimated notional (USD)</dt>
          <dd data-testid="preview-notional">{notional}</dd>
        </dl>
      </Panel>

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

      <button
        type="submit"
        form={FORM_ID}
        disabled={!formValid || isPending}
        style={{ ...buttonStyle(formValid && !isPending), marginTop: "1rem" }}
      >
        {isPending ? "Submitting…" : "Submit Order"}
      </button>
    </>
  );

  return <TwoColumnPage left={leftColumn} right={rightColumn} />;
}
