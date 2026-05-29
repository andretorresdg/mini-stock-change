import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as apiClient from "../../api/client";
import { ApiClientError } from "../../api/client";
import type { OrderResponse } from "../../api/types";
import SubmitOrderForm from "./SubmitOrderForm";

// Mock the entire API client module so no real HTTP calls are made.
vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return { ...actual, submitOrder: vi.fn() };
});

const SAMPLE_ORDER: OrderResponse = {
  order_id: "AAPL-O-1",
  broker_id: "broker1",
  client_order_id: null,
  document_number: "DOC-001",
  side: "ASK",
  symbol: "AAPL",
  price: 15000,
  quantity: 5,
  remaining_quantity: 5,
  filled_quantity: 0,
  status: "OPEN",
  valid_until: "2030-01-01T13:00:00.000Z",
  trades: [],
};

const SAMPLE_ORDER_WITH_TRADES: OrderResponse = {
  ...SAMPLE_ORDER,
  order_id: "AAPL-O-2",
  remaining_quantity: 3,
  filled_quantity: 2,
  status: "PARTIALLY_FILLED",
  trades: [
    {
      trade_id: "T-1",
      sequence: 1,
      symbol: "AAPL",
      buyer_order_id: "AAPL-O-2",
      seller_order_id: "AAPL-O-1",
      buyer_broker_id: "broker2",
      seller_broker_id: "broker1",
      price: 15000,
      quantity: 2,
    },
  ],
};

function renderForm() {
  render(<SubmitOrderForm />);
}

function fillValidForm(overrides: { side?: "BID" | "ASK"; symbol?: string } = {}) {
  fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
    target: { value: "broker1" },
  });
  fireEvent.blur(screen.getByLabelText(/broker \/ username/i));

  fireEvent.change(screen.getByLabelText(/customer document number/i), {
    target: { value: "DOC-001" },
  });
  fireEvent.blur(screen.getByLabelText(/customer document number/i));

  const sideToClick = overrides.side ?? "ASK";
  fireEvent.click(screen.getByRole("radio", { name: sideToClick }));

  fireEvent.change(screen.getByLabelText(/stock symbol/i), {
    target: { value: overrides.symbol ?? "AAPL" },
  });

  fireEvent.change(screen.getByLabelText(/unit price/i), {
    target: { value: "150.00" },
  });
  fireEvent.blur(screen.getByLabelText(/unit price/i));

  fireEvent.change(screen.getByLabelText(/quantity/i), {
    target: { value: "5" },
  });
}

async function submitForm() {
  const btn = screen.getByRole("button", { name: /submit order/i });
  await act(async () => {
    fireEvent.click(btn);
  });
}

afterEach(() => {
  vi.clearAllMocks();
});

// ── Field rendering ──────────────────────────────────────────────────────────

describe("SubmitOrderForm – field rendering", () => {
  it("renders Broker / username field", () => {
    renderForm();
    expect(screen.getByLabelText(/broker \/ username/i)).toBeInTheDocument();
  });

  it("renders Customer document number field", () => {
    renderForm();
    expect(screen.getByLabelText(/customer document number/i)).toBeInTheDocument();
  });

  it("renders the document number helper text", () => {
    renderForm();
    expect(
      screen.getByText(/required to identify the customer represented by the broker/i),
    ).toBeInTheDocument();
  });

  it("renders Order side radio group", () => {
    renderForm();
    expect(screen.getByRole("group", { name: /order side/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "BID" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "ASK" })).toBeInTheDocument();
  });

  it("renders Stock symbol field", () => {
    renderForm();
    expect(screen.getByLabelText(/stock symbol/i)).toBeInTheDocument();
  });

  it("renders Unit price field", () => {
    renderForm();
    expect(screen.getByLabelText(/unit price/i)).toBeInTheDocument();
  });

  it("renders Quantity field", () => {
    renderForm();
    expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
  });

  it("does not render a Client order ID input", () => {
    renderForm();
    expect(screen.queryByLabelText(/client order id/i)).not.toBeInTheDocument();
  });

  it("renders Order validity select", () => {
    renderForm();
    expect(screen.getByLabelText(/order validity/i)).toBeInTheDocument();
  });

  it("renders Submit Order button", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeInTheDocument();
  });
});

// ── Broker ID validation ─────────────────────────────────────────────────────

describe("SubmitOrderForm – broker ID validation", () => {
  it("shows broker ID validation error when field is blurred while empty", () => {
    renderForm();
    fireEvent.blur(screen.getByLabelText(/broker \/ username/i));
    expect(screen.getByText(/broker id must not be empty/i)).toBeInTheDocument();
  });
});

// ── Document number validation ───────────────────────────────────────────────

describe("SubmitOrderForm – document number validation", () => {
  it("shows document number validation error when too short", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/document number/i), {
      target: { value: "AB" },
    });
    fireEvent.blur(screen.getByLabelText(/document number/i));
    expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument();
  });
});

// ── Symbol behaviour ─────────────────────────────────────────────────────────

describe("SubmitOrderForm – symbol input", () => {
  it("uppercases lowercase letters", () => {
    renderForm();
    const input = screen.getByLabelText(/stock symbol/i);
    fireEvent.change(input, { target: { value: "aapl" } });
    expect(input).toHaveValue("AAPL");
  });

  it("does not allow more than 4 letters", () => {
    renderForm();
    const input = screen.getByLabelText(/stock symbol/i);
    fireEvent.change(input, { target: { value: "GOOGL" } });
    expect(input).toHaveValue("GOOG");
  });

  it("removes non-letter characters", () => {
    renderForm();
    const input = screen.getByLabelText(/stock symbol/i);
    fireEvent.change(input, { target: { value: "A1B2" } });
    expect(input).toHaveValue("AB");
  });

  it("shows symbol validation error for invalid symbol", () => {
    renderForm();
    const input = screen.getByLabelText(/stock symbol/i);
    fireEvent.change(input, { target: { value: "1" } });
    fireEvent.blur(input);
    expect(screen.getByText(/symbol must be/i)).toBeInTheDocument();
  });
});

// ── Price behaviour ──────────────────────────────────────────────────────────

describe("SubmitOrderForm – price input", () => {
  it("normalizes price to two decimals on blur", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price/i);
    fireEvent.change(input, { target: { value: "10.5" } });
    fireEvent.blur(input);
    expect(input).toHaveValue("10.50");
  });

  it("normalizes integer price to two decimals on blur", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price/i);
    fireEvent.change(input, { target: { value: "25" } });
    fireEvent.blur(input);
    expect(input).toHaveValue("25.00");
  });

  it("shows price validation error for three decimal places", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price/i);
    fireEvent.change(input, { target: { value: "10.555" } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows price validation error for empty price", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price/i);
    fireEvent.change(input, { target: { value: "1" } });
    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

// ── Quantity behaviour ───────────────────────────────────────────────────────

describe("SubmitOrderForm – quantity input", () => {
  it("keeps digits only in quantity field", () => {
    renderForm();
    const input = screen.getByLabelText(/quantity/i);
    fireEvent.change(input, { target: { value: "10.5" } });
    expect(input).toHaveValue("105");
  });

  it("shows quantity validation error for zero", () => {
    renderForm();
    const input = screen.getByLabelText(/quantity/i);
    fireEvent.change(input, { target: { value: "0" } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows quantity validation error for empty input", () => {
    renderForm();
    const input = screen.getByLabelText(/quantity/i);
    fireEvent.change(input, { target: { value: "1" } });
    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

// ── Submit button state ──────────────────────────────────────────────────────

describe("SubmitOrderForm – submit button", () => {
  it("is disabled when the form is empty", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });

  it("becomes enabled when all required fields are valid", () => {
    renderForm();
    fillValidForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeEnabled();
  });

  it("is disabled after entering an invalid symbol", () => {
    renderForm();
    fillValidForm();
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "1" },
    });
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });
});

// ── Side selection ───────────────────────────────────────────────────────────

describe("SubmitOrderForm – order side", () => {
  it("defaults to BID", () => {
    renderForm();
    expect(screen.getByRole("radio", { name: "BID" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "ASK" })).not.toBeChecked();
  });

  it("can select ASK side", () => {
    renderForm();
    fireEvent.click(screen.getByRole("radio", { name: "ASK" }));
    expect(screen.getByRole("radio", { name: "ASK" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "BID" })).not.toBeChecked();
  });

  it("reflects ASK in the preview", () => {
    renderForm();
    fireEvent.click(screen.getByRole("radio", { name: "ASK" }));
    expect(screen.getByTestId("preview-side")).toHaveTextContent("ASK");
  });
});

// ── Preview summary ──────────────────────────────────────────────────────────

describe("SubmitOrderForm – order preview", () => {
  it("renders the Order preview section", () => {
    renderForm();
    expect(screen.getByRole("region", { name: /order preview/i })).toBeInTheDocument();
  });

  it("shows dashes before any input", () => {
    renderForm();
    expect(screen.getByTestId("preview-symbol")).toHaveTextContent("—");
    expect(screen.getByTestId("preview-price")).toHaveTextContent("—");
    expect(screen.getByTestId("preview-quantity")).toHaveTextContent("—");
  });

  it("reflects valid symbol in the preview", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "TSLA" },
    });
    expect(screen.getByTestId("preview-symbol")).toHaveTextContent("TSLA");
  });

  it("shows estimated notional when price and quantity are valid", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/unit price/i), {
      target: { value: "10.00" },
    });
    fireEvent.blur(screen.getByLabelText(/unit price/i));
    fireEvent.change(screen.getByLabelText(/quantity/i), {
      target: { value: "3" },
    });
    expect(screen.getByTestId("preview-notional")).toHaveTextContent("$30.00");
  });

  it("shows dash for notional when price is invalid", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/unit price/i), {
      target: { value: "abc" },
    });
    fireEvent.change(screen.getByLabelText(/quantity/i), {
      target: { value: "3" },
    });
    expect(screen.getByTestId("preview-notional")).toHaveTextContent("—");
  });

  it("shows dash for preview price when price is a bare dot", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/unit price/i), {
      target: { value: "." },
    });
    expect(screen.getByTestId("preview-price")).toHaveTextContent("—");
  });
});

// ── Optional fields ──────────────────────────────────────────────────────────

describe("SubmitOrderForm – generated client order ID", () => {
  it("is valid without the user entering a client order ID", () => {
    renderForm();
    fillValidForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeEnabled();
  });

  it("does not expose a client order ID input to the user", () => {
    renderForm();
    expect(screen.queryByLabelText(/client order id/i)).not.toBeInTheDocument();
  });
});

// ── Validity / expiration ────────────────────────────────────────────────────

function selectValidityMode(value: "GTC" | "EXPIRES") {
  fireEvent.change(screen.getByLabelText(/order validity/i), { target: { value } });
}

describe("SubmitOrderForm – validity mode", () => {
  it("offers a No expiration (GTC) option", () => {
    renderForm();
    const select = screen.getByLabelText(/order validity/i);
    const labels = Array.from((select as HTMLSelectElement).options).map((o) => o.text);
    expect(labels).toContain("No expiration (GTC)");
  });

  it("defaults to GTC (no expiration)", () => {
    renderForm();
    expect(screen.getByLabelText(/order validity/i)).toHaveValue("GTC");
  });

  it("does not show a datetime input in GTC mode", () => {
    renderForm();
    expect(
      screen.queryByLabelText(/expiration date and time/i),
    ).not.toBeInTheDocument();
  });

  it("shows a datetime input when specific expiration is selected", () => {
    renderForm();
    selectValidityMode("EXPIRES");
    expect(
      screen.getByLabelText(/expiration date and time \(utc\)/i),
    ).toBeInTheDocument();
  });

  it("explains that times are interpreted as UTC", () => {
    renderForm();
    selectValidityMode("EXPIRES");
    expect(screen.getByText(/times are interpreted as utc/i)).toBeInTheDocument();
  });

  it("disables submit when specific expiration is missing", () => {
    renderForm();
    fillValidForm();
    selectValidityMode("EXPIRES");
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });

  it("shows a validation error for a past expiration", () => {
    renderForm();
    fillValidForm();
    selectValidityMode("EXPIRES");
    const input = screen.getByLabelText(/expiration date and time \(utc\)/i);
    fireEvent.change(input, { target: { value: "2000-01-01T00:00" } });
    expect(screen.getByText(/must be in the future/i)).toBeInTheDocument();
  });
});

// ── API integration – payload ────────────────────────────────────────────────

describe("SubmitOrderForm – API payload", () => {
  beforeEach(() => {
    vi.mocked(apiClient.submitOrder).mockResolvedValue(SAMPLE_ORDER);
  });

  it("sends correct ASK payload with price as integer cents", async () => {
    renderForm();
    fillValidForm({ side: "ASK" });
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [brokerId, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(brokerId).toBe("broker1");
    expect(req.side).toBe("ASK");
    expect(req.symbol).toBe("AAPL");
    expect(req.price).toBe(15000); // 150.00 → 15000 cents
    expect(req.quantity).toBe(5);
    expect(req.document_number).toBe("DOC-001");
    // Default validity is GTC, so valid_until is null.
    expect(req.valid_until).toBeNull();
  });

  it("sends correct BID payload", async () => {
    renderForm();
    fillValidForm({ side: "BID" });
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.side).toBe("BID");
  });

  it("sends broker_id as path parameter (first argument)", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [brokerId] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(brokerId).toBe("broker1");
  });

  it("sends quantity as integer", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(Number.isInteger(req.quantity)).toBe(true);
  });

  it("sends a generated non-empty client_order_id", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(typeof req.client_order_id).toBe("string");
    expect((req.client_order_id ?? "").length).toBeGreaterThan(0);
  });

  it("uses a fallback client_order_id when crypto.randomUUID is unavailable", async () => {
    const original = crypto.randomUUID;
    // @ts-expect-error deliberately removing randomUUID to test the fallback
    crypto.randomUUID = undefined;
    try {
      renderForm();
      fillValidForm();
      await submitForm();

      await waitFor(() => {
        expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
      });

      const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
      expect(req.client_order_id).toMatch(/^cli-/);
    } finally {
      crypto.randomUUID = original;
    }
  });

  it("sends valid_until null for a GTC order (default)", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.valid_until).toBeNull();
  });

  it("sends a UTC ISO string ending in Z for a specific expiration", async () => {
    renderForm();
    fillValidForm();
    fireEvent.change(screen.getByLabelText(/order validity/i), {
      target: { value: "EXPIRES" },
    });
    fireEvent.change(screen.getByLabelText(/expiration date and time \(utc\)/i), {
      target: { value: "2099-05-28T15:30" },
    });
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.valid_until).toBe("2099-05-28T15:30:00Z");
  });
});

// ── Price input clarity ──────────────────────────────────────────────────────

describe("SubmitOrderForm – price input", () => {
  it("labels the price field as Unit price (USD)", () => {
    renderForm();
    expect(screen.getByLabelText(/unit price \(usd\)/i)).toBeInTheDocument();
  });

  it("shows the dot decimal helper text", () => {
    renderForm();
    expect(
      screen.getByText(/use a dot as decimal separator, for example 10\.50/i),
    ).toBeInTheDocument();
  });

  it("has a 10.00 placeholder", () => {
    renderForm();
    expect(screen.getByLabelText(/unit price \(usd\)/i)).toHaveAttribute(
      "placeholder",
      "10.00",
    );
  });

  it("normalizes 10 to 10.00 on blur", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price \(usd\)/i);
    fireEvent.change(input, { target: { value: "10" } });
    fireEvent.blur(input);
    expect(input).toHaveValue("10.00");
  });

  it("normalizes 10.5 to 10.50 on blur", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price \(usd\)/i);
    fireEvent.change(input, { target: { value: "10.5" } });
    fireEvent.blur(input);
    expect(input).toHaveValue("10.50");
  });

  it("keeps 10.50 as 10.50 on blur", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price \(usd\)/i);
    fireEvent.change(input, { target: { value: "10.50" } });
    fireEvent.blur(input);
    expect(input).toHaveValue("10.50");
  });

  it("rejects comma decimal input with a clear message", () => {
    renderForm();
    const input = screen.getByLabelText(/unit price \(usd\)/i);
    fireEvent.change(input, { target: { value: "10,50" } });
    expect(screen.getByRole("alert")).toHaveTextContent(
      /use a dot as decimal separator, for example 10\.50/i,
    );
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });

  it("submits 10.50 as 1050 integer cents", async () => {
    vi.mocked(apiClient.submitOrder).mockResolvedValue(SAMPLE_ORDER);
    renderForm();
    fillValidForm();
    const input = screen.getByLabelText(/unit price \(usd\)/i);
    fireEvent.change(input, { target: { value: "10.50" } });
    fireEvent.blur(input);
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.price).toBe(1050);
  });
});

// ── Loading state ────────────────────────────────────────────────────────────

describe("SubmitOrderForm – loading state", () => {
  it("shows Submitting… while the request is in flight", async () => {
    // Never resolves — simulates a slow request
    vi.mocked(apiClient.submitOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /submitting/i })).toBeInTheDocument();
    });
  });

  it("disables the submit button while pending", async () => {
    vi.mocked(apiClient.submitOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /submitting/i })).toBeDisabled();
    });
  });

  it("does not submit again while already pending", async () => {
    vi.mocked(apiClient.submitOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillValidForm();
    await submitForm(); // first submit

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /submitting/i })).toBeDisabled();
    });

    // Submit via the form element directly — guard in handleSubmit stops it.
    const form = screen.getByRole("button", { name: /submitting/i }).closest("form")!;
    fireEvent.submit(form);

    expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
  });
});

// ── Success state ────────────────────────────────────────────────────────────

describe("SubmitOrderForm – success state", () => {
  beforeEach(() => {
    vi.mocked(apiClient.submitOrder).mockResolvedValue(SAMPLE_ORDER);
  });

  it("shows the order ID after successful submission", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByTestId("success-order-id")).toHaveTextContent("AAPL-O-1");
    });
  });

  it("shows the save-order-ID instruction", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(
        screen.getByText(/save this order id/i),
      ).toBeInTheDocument();
    });
  });

  it("shows order status, remaining quantity, and filled quantity", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByTestId("success-status")).toHaveTextContent("OPEN");
      expect(screen.getByTestId("success-remaining")).toHaveTextContent("5");
      expect(screen.getByTestId("success-filled")).toHaveTextContent("0");
    });
  });

  it("displays No expiration for a GTC order instead of raw null", async () => {
    vi.mocked(apiClient.submitOrder).mockResolvedValue({
      ...SAMPLE_ORDER,
      valid_until: null,
    });
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByTestId("success-validity")).toHaveTextContent(/no expiration/i);
    });
    expect(screen.getByTestId("success-validity")).not.toHaveTextContent("null");
  });

  it("does not render trades table when there are no trades", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.queryByRole("table", { name: /trades/i })).not.toBeInTheDocument();
    });
  });

  it("renders trades table when trades exist", async () => {
    vi.mocked(apiClient.submitOrder).mockResolvedValue(SAMPLE_ORDER_WITH_TRADES);
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("table", { name: /trades/i })).toBeInTheDocument();
      expect(screen.getByText("T-1")).toBeInTheDocument();
    });
  });

  it("resets the form when 'Submit another order' is clicked", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByTestId("success-order-id")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /submit another order/i }));

    expect(screen.getByLabelText(/broker \/ username/i)).toHaveValue("");
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });
});

// ── Error state ──────────────────────────────────────────────────────────────

describe("SubmitOrderForm – error state", () => {
  it("shows API error message", async () => {
    vi.mocked(apiClient.submitOrder).mockRejectedValue(
      new ApiClientError({ code: "EXPIRED_ORDER", message: "order has expired", status: 400 }),
    );
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("order has expired");
    });
  });

  it("shows network error message", async () => {
    vi.mocked(apiClient.submitOrder).mockRejectedValue(
      new ApiClientError({
        code: "NETWORK_ERROR",
        message: "Failed to fetch",
        status: 0,
      }),
    );
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to fetch");
    });
  });

  it("shows generic message for unexpected errors", async () => {
    vi.mocked(apiClient.submitOrder).mockRejectedValue(new Error("surprise"));
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    });
  });

  it("keeps form data intact after an error", async () => {
    vi.mocked(apiClient.submitOrder).mockRejectedValue(
      new ApiClientError({ code: "SERVER_ERROR", message: "server error", status: 500 }),
    );
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    // Form data is still present
    expect(screen.getByLabelText(/broker \/ username/i)).toHaveValue("broker1");
    expect(screen.getByLabelText(/stock symbol/i)).toHaveValue("AAPL");
  });

  it("re-enables the submit button after an error", async () => {
    vi.mocked(apiClient.submitOrder).mockRejectedValue(
      new ApiClientError({ code: "SERVER_ERROR", message: "server error", status: 500 }),
    );
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /submit order/i })).toBeEnabled();
    });
  });
});
