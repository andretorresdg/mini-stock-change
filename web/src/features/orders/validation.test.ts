import { describe, expect, it } from "vitest";
import {
  buildDefaultValidUntil,
  normalizePriceDisplay,
  priceToCents,
  quantityToApiInteger,
  sanitizePriceInput,
  sanitizeQuantityInput,
  sanitizeSymbolInput,
  validateBrokerId,
  validateDocumentNumber,
  validateOrderId,
  validatePrice,
  validateQuantity,
  validateSymbol,
} from "./validation";

// ── Symbol ────────────────────────────────────────────────────────────────────

describe("sanitizeSymbolInput", () => {
  it("uppercases lowercase letters", () => {
    expect(sanitizeSymbolInput("aapl")).toBe("AAPL");
  });

  it("removes non-letter characters", () => {
    expect(sanitizeSymbolInput("A1B2C")).toBe("ABC");
  });

  it("truncates to 4 letters", () => {
    expect(sanitizeSymbolInput("GOOGL")).toBe("GOOG");
  });

  it("removes spaces and special characters", () => {
    expect(sanitizeSymbolInput("A B!C")).toBe("ABC");
  });

  it("returns empty string for all non-letters", () => {
    expect(sanitizeSymbolInput("123")).toBe("");
  });

  it("passes through a valid 4-letter symbol unchanged", () => {
    expect(sanitizeSymbolInput("TSLA")).toBe("TSLA");
  });
});

describe("validateSymbol", () => {
  it("returns null for valid 1-letter symbol", () => {
    expect(validateSymbol("A")).toBeNull();
  });

  it("returns null for valid 4-letter symbol", () => {
    expect(validateSymbol("AAPL")).toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateSymbol("")).not.toBeNull();
  });

  it("returns error for 5 letters", () => {
    expect(validateSymbol("GOOGL")).not.toBeNull();
  });

  it("returns error for lowercase letters", () => {
    expect(validateSymbol("aapl")).not.toBeNull();
  });

  it("returns error for digits in symbol", () => {
    expect(validateSymbol("AA1")).not.toBeNull();
  });
});

// ── Quantity ──────────────────────────────────────────────────────────────────

describe("sanitizeQuantityInput", () => {
  it("removes non-digit characters", () => {
    expect(sanitizeQuantityInput("10.5")).toBe("105");
  });

  it("removes letters", () => {
    expect(sanitizeQuantityInput("10abc")).toBe("10");
  });

  it("keeps digits only", () => {
    expect(sanitizeQuantityInput("100")).toBe("100");
  });

  it("returns empty string for all non-digits", () => {
    expect(sanitizeQuantityInput("abc")).toBe("");
  });
});

describe("validateQuantity", () => {
  it("returns null for valid quantity", () => {
    expect(validateQuantity("1")).toBeNull();
  });

  it("returns null for large quantity", () => {
    expect(validateQuantity("9999")).toBeNull();
  });

  it("returns error for zero", () => {
    expect(validateQuantity("0")).not.toBeNull();
  });

  it("returns error for negative string", () => {
    expect(validateQuantity("-1")).not.toBeNull();
  });

  it("returns error for decimal", () => {
    expect(validateQuantity("1.5")).not.toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateQuantity("")).not.toBeNull();
  });

  it("returns error for non-numeric string", () => {
    expect(validateQuantity("abc")).not.toBeNull();
  });
});

describe("quantityToApiInteger", () => {
  it("converts string to integer", () => {
    expect(quantityToApiInteger("42")).toBe(42);
  });

  it("converts large quantity", () => {
    expect(quantityToApiInteger("10000")).toBe(10000);
  });
});

// ── Price ─────────────────────────────────────────────────────────────────────

describe("sanitizePriceInput", () => {
  it("removes non-numeric non-dot characters", () => {
    expect(sanitizePriceInput("$10.50")).toBe("10.50");
  });

  it("keeps a single decimal point", () => {
    expect(sanitizePriceInput("10.5")).toBe("10.5");
  });

  it("removes extra decimal points", () => {
    expect(sanitizePriceInput("1.2.3")).toBe("1.23");
  });

  it("passes digits-only through unchanged", () => {
    expect(sanitizePriceInput("100")).toBe("100");
  });
});

describe("normalizePriceDisplay", () => {
  it("normalizes integer to two decimals", () => {
    expect(normalizePriceDisplay("10")).toBe("10.00");
  });

  it("normalizes one decimal to two decimals", () => {
    expect(normalizePriceDisplay("10.5")).toBe("10.50");
  });

  it("leaves two decimals unchanged", () => {
    expect(normalizePriceDisplay("10.55")).toBe("10.55");
  });

  it("returns empty string for empty input", () => {
    expect(normalizePriceDisplay("")).toBe("");
  });

  it("returns empty string for bare dot", () => {
    expect(normalizePriceDisplay(".")).toBe("");
  });

  it("returns the value unchanged for zero", () => {
    expect(normalizePriceDisplay("0")).toBe("0");
  });
});

describe("validatePrice", () => {
  it("returns null for valid integer price", () => {
    expect(validatePrice("10")).toBeNull();
  });

  it("returns null for one decimal place", () => {
    expect(validatePrice("10.5")).toBeNull();
  });

  it("returns null for two decimal places", () => {
    expect(validatePrice("10.55")).toBeNull();
  });

  it("returns error for three decimal places", () => {
    expect(validatePrice("10.555")).not.toBeNull();
  });

  it("returns error for zero", () => {
    expect(validatePrice("0")).not.toBeNull();
  });

  it("returns error for negative value", () => {
    expect(validatePrice("-1")).not.toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validatePrice("")).not.toBeNull();
  });

  it("returns error for non-numeric", () => {
    expect(validatePrice("abc")).not.toBeNull();
  });

  it("returns error for value with letters", () => {
    expect(validatePrice("10a")).not.toBeNull();
  });
});

describe("priceToCents", () => {
  it("converts integer string to cents", () => {
    expect(priceToCents("10")).toBe(1000);
  });

  it("converts one decimal to cents", () => {
    expect(priceToCents("10.5")).toBe(1050);
  });

  it("converts two decimals to cents", () => {
    expect(priceToCents("10.55")).toBe(1055);
  });

  it("converts 1 to 100 cents", () => {
    expect(priceToCents("1")).toBe(100);
  });

  it("converts 0.01 to 1 cent", () => {
    expect(priceToCents("0.01")).toBe(1);
  });

  it("avoids floating point rounding on 10.1", () => {
    // 10.1 * 100 === 1009.9999... in floats; string parsing gives exactly 1010
    expect(priceToCents("10.1")).toBe(1010);
  });

  it("avoids floating point rounding on 2.23", () => {
    // 2.23 * 100 === 222.99999... in floats; string parsing gives exactly 223
    expect(priceToCents("2.23")).toBe(223);
  });

  it("converts large price correctly", () => {
    expect(priceToCents("999.99")).toBe(99999);
  });
});

// ── Broker ID ─────────────────────────────────────────────────────────────────

describe("validateBrokerId", () => {
  it("returns null for a valid alphanumeric broker ID", () => {
    expect(validateBrokerId("broker1")).toBeNull();
  });

  it("returns null for ID with dots, underscores, dashes", () => {
    expect(validateBrokerId("my.broker_id-01")).toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateBrokerId("")).not.toBeNull();
  });

  it("returns error for whitespace-only string", () => {
    expect(validateBrokerId("   ")).not.toBeNull();
  });

  it("returns error for ID exceeding 64 characters", () => {
    expect(validateBrokerId("a".repeat(65))).not.toBeNull();
  });

  it("returns null for exactly 64 characters", () => {
    expect(validateBrokerId("a".repeat(64))).toBeNull();
  });

  it("returns error for ID with special characters", () => {
    expect(validateBrokerId("broker!id")).not.toBeNull();
  });

  it("returns error for ID with spaces", () => {
    expect(validateBrokerId("broker id")).not.toBeNull();
  });
});

// ── Document number ───────────────────────────────────────────────────────────

describe("validateDocumentNumber", () => {
  it("returns null for valid document number", () => {
    expect(validateDocumentNumber("DOC-001")).toBeNull();
  });

  it("returns null for document with slashes", () => {
    expect(validateDocumentNumber("DOC/2024/001")).toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateDocumentNumber("")).not.toBeNull();
  });

  it("returns error for string shorter than 3 characters", () => {
    expect(validateDocumentNumber("AB")).not.toBeNull();
  });

  it("returns null for exactly 3 characters", () => {
    expect(validateDocumentNumber("ABC")).toBeNull();
  });

  it("returns error for string longer than 32 characters", () => {
    expect(validateDocumentNumber("A".repeat(33))).not.toBeNull();
  });

  it("returns null for exactly 32 characters", () => {
    expect(validateDocumentNumber("A".repeat(32))).toBeNull();
  });

  it("returns error for document with spaces", () => {
    expect(validateDocumentNumber("DOC 001")).not.toBeNull();
  });

  it("returns error for document with special characters", () => {
    expect(validateDocumentNumber("DOC@001")).not.toBeNull();
  });
});

// ── Order ID ──────────────────────────────────────────────────────────────────

describe("validateOrderId", () => {
  it("returns null for a valid order ID", () => {
    expect(validateOrderId("AAPL-O-1")).toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateOrderId("")).not.toBeNull();
  });

  it("returns error for whitespace-only string", () => {
    expect(validateOrderId("   ")).not.toBeNull();
  });

  it("returns null for ID at exactly 128 characters", () => {
    expect(validateOrderId("A".repeat(128))).toBeNull();
  });

  it("returns error for ID longer than 128 characters after trim", () => {
    expect(validateOrderId("A".repeat(129))).not.toBeNull();
  });

  it("accepts ID with surrounding whitespace as valid when trimmed", () => {
    expect(validateOrderId("  AAPL-O-1  ")).toBeNull();
  });
});

// ── Validity window ───────────────────────────────────────────────────────────

describe("buildDefaultValidUntil", () => {
  const FIXED_NOW = new Date("2030-01-01T12:00:00.000Z");
  const fixedClock = () => FIXED_NOW;

  it("adds 60 minutes by default", () => {
    const result = buildDefaultValidUntil(undefined, fixedClock);
    expect(result).toBe("2030-01-01T13:00:00.000Z");
  });

  it("adds a custom number of minutes", () => {
    const result = buildDefaultValidUntil(30, fixedClock);
    expect(result).toBe("2030-01-01T12:30:00.000Z");
  });

  it("returns an ISO string", () => {
    const result = buildDefaultValidUntil(60, fixedClock);
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  });

  it("uses real clock when no clock provided", () => {
    const before = Date.now();
    const result = buildDefaultValidUntil(60);
    const after = Date.now();
    const resultMs = new Date(result).getTime();
    expect(resultMs).toBeGreaterThanOrEqual(before + 60 * 60 * 1000);
    expect(resultMs).toBeLessThanOrEqual(after + 60 * 60 * 1000);
  });
});
