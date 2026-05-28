// API uses integer cents; UI uses decimal strings to avoid
// floating point money bugs. All cent conversion is done via
// string parsing, never via arithmetic on floats.

// ── Symbol ────────────────────────────────────────────────────────────────────

export function sanitizeSymbolInput(value: string): string {
  return value.replace(/[^A-Za-z]/g, "").toUpperCase().slice(0, 4);
}

export function validateSymbol(value: string): string | null {
  if (!/^[A-Z]{1,4}$/.test(value)) {
    return "Symbol must be 1–4 uppercase letters.";
  }
  return null;
}

// ── Quantity ──────────────────────────────────────────────────────────────────

export function sanitizeQuantityInput(value: string): string {
  return value.replace(/\D/g, "");
}

export function validateQuantity(value: string): string | null {
  if (!/^\d+$/.test(value)) {
    return "Quantity must be a positive integer.";
  }
  const n = parseInt(value, 10);
  if (n <= 0) {
    return "Quantity must be greater than zero.";
  }
  return null;
}

export function quantityToApiInteger(value: string): number {
  return parseInt(value, 10);
}

// ── Price ─────────────────────────────────────────────────────────────────────

export function sanitizePriceInput(value: string): string {
  // Keep digits and at most one decimal point.
  let result = value.replace(/[^\d.]/g, "");
  const dotIndex = result.indexOf(".");
  if (dotIndex !== -1) {
    result =
      result.slice(0, dotIndex + 1) +
      result.slice(dotIndex + 1).replace(/\./g, "");
  }
  return result;
}

export function normalizePriceDisplay(value: string): string {
  if (value === "" || value === ".") return "";
  const n = parseFloat(value);
  if (!isFinite(n) || n <= 0) return value;
  return n.toFixed(2);
}

export function validatePrice(value: string): string | null {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) {
    return "Price must be a positive number with at most two decimal places.";
  }
  const n = parseFloat(value);
  if (!isFinite(n) || n <= 0) {
    return "Price must be greater than zero.";
  }
  return null;
}

export function priceToCents(value: string): number {
  // Split on the decimal point and pad or trim to exactly two decimals.
  const [intPart, fracPart = ""] = value.split(".");
  const cents = fracPart.slice(0, 2).padEnd(2, "0");
  return parseInt(intPart + cents, 10);
}

// ── Broker ID ─────────────────────────────────────────────────────────────────

export function validateBrokerId(value: string): string | null {
  if (value.trim().length === 0) {
    return "Broker ID must not be empty.";
  }
  if (value.length > 64) {
    return "Broker ID must be at most 64 characters.";
  }
  if (!/^[A-Za-z0-9._-]+$/.test(value)) {
    return "Broker ID may only contain letters, digits, dots, underscores, and dashes.";
  }
  return null;
}

// ── Document number ───────────────────────────────────────────────────────────

export function validateDocumentNumber(value: string): string | null {
  if (value.trim().length === 0) {
    return "Document number must not be empty.";
  }
  if (value.length < 3) {
    return "Document number must be at least 3 characters.";
  }
  if (value.length > 32) {
    return "Document number must be at most 32 characters.";
  }
  if (!/^[A-Za-z0-9.\-/]+$/.test(value)) {
    return "Document number may only contain letters, digits, dots, dashes, and slashes.";
  }
  return null;
}

// ── Order ID ──────────────────────────────────────────────────────────────────

export function validateOrderId(value: string): string | null {
  if (value.trim().length === 0) {
    return "Order ID must not be empty.";
  }
  if (value.trim().length > 128) {
    return "Order ID must be at most 128 characters.";
  }
  return null;
}

// ── Validity window ───────────────────────────────────────────────────────────

export function buildDefaultValidUntil(
  minutes = 60,
  clock: () => Date = () => new Date(),
): string {
  const now = clock();
  const future = new Date(now.getTime() + minutes * 60 * 1000);
  return future.toISOString();
}
