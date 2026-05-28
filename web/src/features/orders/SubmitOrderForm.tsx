import { useState } from "react";
import type { OrderSide } from "../../api/types";
import {
  normalizePriceDisplay,
  priceToCents,
  quantityToApiInteger,
  sanitizePriceInput,
  sanitizeQuantityInput,
  sanitizeSymbolInput,
  validateBrokerId,
  validateDocumentNumber,
  validatePrice,
  validateQuantity,
  validateSymbol,
} from "./validation";

// backend requires valid_until.
// MVP uses a simple validity window instead of advanced order duration types.
const VALIDITY_OPTIONS = [
  { label: "15 minutes", minutes: 15 },
  { label: "1 hour", minutes: 60 },
  { label: "4 hours", minutes: 240 },
  { label: "1 day", minutes: 1440 },
] as const;

const DEFAULT_VALIDITY_MINUTES = 60;

interface FormState {
  brokerId: string;
  documentNumber: string;
  side: OrderSide;
  symbol: string;
  price: string;
  quantity: string;
  clientOrderId: string;
  validityMinutes: number;
}

interface FormErrors {
  brokerId: string | null;
  documentNumber: string | null;
  symbol: string | null;
  price: string | null;
  quantity: string | null;
}

function validate(state: FormState): FormErrors {
  return {
    brokerId: validateBrokerId(state.brokerId),
    documentNumber: validateDocumentNumber(state.documentNumber),
    symbol: validateSymbol(state.symbol),
    price: validatePrice(state.price),
    quantity: validateQuantity(state.quantity),
  };
}

function isValid(errors: FormErrors): boolean {
  return Object.values(errors).every((e) => e === null);
}

interface SubmitOrderFormProps {
  isPending?: boolean;
}

export default function SubmitOrderForm({ isPending = false }: SubmitOrderFormProps) {
  const [form, setForm] = useState<FormState>({
    brokerId: "",
    documentNumber: "",
    side: "BID",
    symbol: "",
    price: "",
    quantity: "",
    clientOrderId: "",
    validityMinutes: DEFAULT_VALIDITY_MINUTES,
  });

  const [touched, setTouched] = useState<Partial<Record<keyof FormErrors, boolean>>>({});

  const errors = validate(form);
  const formValid = isValid(errors);

  function touch(field: keyof FormErrors) {
    setTouched((t) => ({ ...t, [field]: true }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // API wiring comes in a future commit.
  }

  // Preview values
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

  return (
    <form onSubmit={handleSubmit} noValidate>
      {/* Broker / username */}
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

      {/* Document number */}
      <div style={fieldStyle}>
        <label htmlFor="documentNumber" style={labelStyle}>
          Document number
        </label>
        <input
          id="documentNumber"
          type="text"
          autoComplete="off"
          value={form.documentNumber}
          onChange={(e) => setForm((f) => ({ ...f, documentNumber: e.target.value }))}
          onBlur={() => touch("documentNumber")}
          aria-describedby={
            touched.documentNumber && errors.documentNumber ? "documentNumberError" : undefined
          }
          style={inputStyle}
        />
        {touched.documentNumber && errors.documentNumber && (
          <span id="documentNumberError" role="alert" style={errorStyle}>
            {errors.documentNumber}
          </span>
        )}
      </div>

      {/* Order side */}
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

      {/* Stock symbol */}
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

      {/* Unit price */}
      <div style={fieldStyle}>
        <label htmlFor="price" style={labelStyle}>
          Unit price
        </label>
        <input
          id="price"
          type="text"
          inputMode="decimal"
          autoComplete="off"
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
          aria-describedby={touched.price && errors.price ? "priceError" : undefined}
          style={inputStyle}
        />
        {touched.price && errors.price && (
          <span id="priceError" role="alert" style={errorStyle}>
            {errors.price}
          </span>
        )}
      </div>

      {/* Quantity */}
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

      {/* Client order ID (optional) */}
      <div style={fieldStyle}>
        <label htmlFor="clientOrderId" style={labelStyle}>
          Client order ID{" "}
          <span style={{ fontWeight: 400, color: "#718096" }}>
            (optional – helps make retries idempotent)
          </span>
        </label>
        <input
          id="clientOrderId"
          type="text"
          autoComplete="off"
          value={form.clientOrderId}
          onChange={(e) => setForm((f) => ({ ...f, clientOrderId: e.target.value }))}
          style={inputStyle}
        />
      </div>

      {/* Validity window */}
      <div style={fieldStyle}>
        <label htmlFor="validityMinutes" style={labelStyle}>
          Order validity
        </label>
        <select
          id="validityMinutes"
          value={form.validityMinutes}
          onChange={(e) =>
            setForm((f) => ({ ...f, validityMinutes: parseInt(e.target.value, 10) }))
          }
          style={inputStyle}
        >
          {VALIDITY_OPTIONS.map((opt) => (
            <option key={opt.minutes} value={opt.minutes}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Order preview */}
      <section
        aria-labelledby="previewHeading"
        style={{
          background: "#1a202c",
          border: "1px solid #2d3748",
          borderRadius: "6px",
          padding: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2
          id="previewHeading"
          style={{ fontSize: "0.9rem", color: "#a0aec0", marginBottom: "0.75rem" }}
        >
          Order preview
        </h2>
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
          <dt style={{ color: "#718096" }}>Est. notional</dt>
          <dd data-testid="preview-notional">{notional}</dd>
        </dl>
      </section>

      {/* Placeholder for future success / error feedback */}
      <div role="status" aria-live="polite" aria-label="Order submission status" />

      {/* Submit */}
      <button
        type="submit"
        disabled={!formValid || isPending}
        style={{
          padding: "0.6rem 1.5rem",
          background: formValid && !isPending ? "#3182ce" : "#2d3748",
          color: "#e2e8f0",
          border: "none",
          borderRadius: "4px",
          fontSize: "1rem",
          cursor: formValid && !isPending ? "pointer" : "not-allowed",
        }}
      >
        Submit Order
      </button>
    </form>
  );
}
