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

  fireEvent.change(screen.getByLabelText(/document number/i), {
    target: { value: "DOC-001" },
  });
  fireEvent.blur(screen.getByLabelText(/document number/i));

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

  it("renders Document number field", () => {
    renderForm();
    expect(screen.getByLabelText(/document number/i)).toBeInTheDocument();
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

  it("renders Client order ID field", () => {
    renderForm();
    expect(screen.getByLabelText(/client order id/i)).toBeInTheDocument();
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

describe("SubmitOrderForm – optional client order ID", () => {
  it("allows the form to be valid with an empty client order ID", () => {
    renderForm();
    fillValidForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeEnabled();
  });

  it("accepts a client order ID value", () => {
    renderForm();
    const input = screen.getByLabelText(/client order id/i);
    fireEvent.change(input, { target: { value: "my-order-123" } });
    expect(input).toHaveValue("my-order-123");
  });
});

// ── Validity window ──────────────────────────────────────────────────────────

describe("SubmitOrderForm – validity window", () => {
  it("defaults to 1 hour (60 minutes)", () => {
    renderForm();
    const select = screen.getByLabelText(/order validity/i);
    expect(select).toHaveValue("60");
  });

  it("offers 15 minutes, 1 hour, 4 hours, and 1 day options", () => {
    renderForm();
    const select = screen.getByLabelText(/order validity/i);
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.value);
    expect(options).toEqual(["15", "60", "240", "1440"]);
  });

  it("can change the validity window", () => {
    renderForm();
    const select = screen.getByLabelText(/order validity/i);
    fireEvent.change(select, { target: { value: "1440" } });
    expect(select).toHaveValue("1440");
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
    expect(typeof req.valid_until).toBe("string");
    expect(req.valid_until).toMatch(/^\d{4}-\d{2}-\d{2}T/);
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

  it("sends client_order_id as null when empty", async () => {
    renderForm();
    fillValidForm();
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.client_order_id).toBeNull();
  });

  it("sends client_order_id when provided", async () => {
    renderForm();
    fillValidForm();
    fireEvent.change(screen.getByLabelText(/client order id/i), {
      target: { value: "my-ref-001" },
    });
    await submitForm();

    await waitFor(() => {
      expect(vi.mocked(apiClient.submitOrder)).toHaveBeenCalledOnce();
    });

    const [, req] = vi.mocked(apiClient.submitOrder).mock.calls[0]!;
    expect(req.client_order_id).toBe("my-ref-001");
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
