import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as apiClient from "../../api/client";
import { ApiClientError } from "../../api/client";
import type { OrderResponse } from "../../api/types";
import OrderLookupForm from "./OrderLookupForm";

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return { ...actual, getOrder: vi.fn() };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: 0, gcTime: 0, refetchOnWindowFocus: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const OPEN_ORDER: OrderResponse = {
  order_id: "AAPL-O-1",
  broker_id: "broker1",
  client_order_id: null,
  document_number: "DOC-001",
  side: "ASK",
  symbol: "AAPL",
  price: 15000,
  quantity: 10,
  remaining_quantity: 10,
  filled_quantity: 0,
  status: "OPEN",
  valid_until: "2030-01-01T13:00:00.000Z",
  trades: [],
};

const ORDER_WITH_TRADES: OrderResponse = {
  ...OPEN_ORDER,
  order_id: "AAPL-O-2",
  status: "PARTIALLY_FILLED",
  remaining_quantity: 7,
  filled_quantity: 3,
  trades: [
    {
      trade_id: "T-1",
      sequence: 1,
      symbol: "AAPL",
      buyer_order_id: "AAPL-O-2",
      seller_order_id: "AAPL-O-3",
      buyer_broker_id: "broker1",
      seller_broker_id: "broker2",
      price: 15000,
      quantity: 3,
    },
  ],
};

const ORDER_WITH_CLIENT_ID: OrderResponse = {
  ...OPEN_ORDER,
  client_order_id: "my-ref-001",
};

const FILLED_ORDER: OrderResponse = { ...OPEN_ORDER, status: "FILLED" };

afterEach(() => {
  vi.resetAllMocks();
});

function renderForm() {
  render(<OrderLookupForm />, { wrapper: createWrapper() });
}

function fillForm(broker = "broker1", order = "AAPL-O-1") {
  fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
    target: { value: broker },
  });
  fireEvent.change(screen.getByLabelText(/order id/i), {
    target: { value: order },
  });
}

async function submitLookup() {
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /look up order/i }));
  });
}

// ── Rendering ────────────────────────────────────────────────────────────────

describe("OrderLookupForm – rendering", () => {
  it("renders broker / username field", () => {
    renderForm();
    expect(screen.getByLabelText(/broker \/ username/i)).toBeInTheDocument();
  });

  it("renders order ID field", () => {
    renderForm();
    expect(screen.getByLabelText(/order id/i)).toBeInTheDocument();
  });

  it("renders Look up order button", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /look up order/i })).toBeInTheDocument();
  });

  it("renders ownership hint explaining the order must belong to the broker/user", () => {
    renderForm();
    expect(screen.getByText(/order must belong to the specified broker\/user/i)).toBeInTheDocument();
  });

  it("shows empty state before lookup", () => {
    renderForm();
    expect(
      screen.getByText(/enter a broker id and order id to view order status/i),
    ).toBeInTheDocument();
  });
});

// ── Validation / button state ─────────────────────────────────────────────────

describe("OrderLookupForm – validation", () => {
  it("disables lookup button when form is empty", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /look up order/i })).toBeDisabled();
  });

  it("disables lookup button when broker ID is invalid", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
      target: { value: "broker with spaces" },
    });
    fireEvent.change(screen.getByLabelText(/order id/i), {
      target: { value: "AAPL-O-1" },
    });
    expect(screen.getByRole("button", { name: /look up order/i })).toBeDisabled();
  });

  it("disables lookup button when order ID is empty", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
      target: { value: "broker1" },
    });
    expect(screen.getByRole("button", { name: /look up order/i })).toBeDisabled();
  });

  it("enables lookup button when both fields are valid", () => {
    renderForm();
    fillForm();
    expect(screen.getByRole("button", { name: /look up order/i })).toBeEnabled();
  });

  it("shows broker ID validation error on blur when empty", () => {
    renderForm();
    fireEvent.blur(screen.getByLabelText(/broker \/ username/i));
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows order ID validation error on blur when empty", () => {
    renderForm();
    fireEvent.blur(screen.getByLabelText(/order id/i));
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

// ── Query guard ───────────────────────────────────────────────────────────────

describe("OrderLookupForm – query guard", () => {
  it("does not call getOrder before the user submits", async () => {
    renderForm();
    fillForm();
    // No submit
    await act(async () => {
      await Promise.resolve();
    });
    expect(vi.mocked(apiClient.getOrder)).not.toHaveBeenCalled();
  });

  it("does not re-query when input values change after first submission", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm("broker1", "AAPL-O-1");
    await submitLookup();

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(1);
    });

    // Change inputs without submitting
    fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
      target: { value: "broker2" },
    });
    fireEvent.change(screen.getByLabelText(/order id/i), {
      target: { value: "AAPL-O-99" },
    });

    // Allow any potential async effects to settle
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(apiClient.getOrder)).not.toHaveBeenCalledWith(
      "broker2",
      "AAPL-O-99",
    );
  });
});

// ── API call ─────────────────────────────────────────────────────────────────

describe("OrderLookupForm – API call", () => {
  beforeEach(() => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
  });

  it("calls getOrder with broker_id and order_id", async () => {
    renderForm();
    fillForm("broker1", "AAPL-O-1");
    await submitLookup();

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledWith("broker1", "AAPL-O-1");
    });
  });

  it("trims whitespace from order ID before calling API", async () => {
    renderForm();
    fillForm("broker1", "  AAPL-O-1  ");
    await submitLookup();

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledWith("broker1", "AAPL-O-1");
    });
  });

  it("fetches once on manual lookup", async () => {
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(1);
    });
  });

  it("re-submitting the same pair calls getOrder again via refetch", async () => {
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByTestId("detail-order-id")).toBeInTheDocument();
    });

    // Submit again with the same pair values
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /look up order/i }));
    });

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);
    });
  });
});

// ── Loading state ─────────────────────────────────────────────────────────────

describe("OrderLookupForm – loading state", () => {
  it("shows Looking up… while request is in flight", async () => {
    vi.mocked(apiClient.getOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /looking up/i })).toBeInTheDocument();
    });
  });

  it("disables the button while loading", async () => {
    vi.mocked(apiClient.getOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /looking up/i })).toBeDisabled();
    });
  });

  it("does not call getOrder a second time if submitted while loading", async () => {
    vi.mocked(apiClient.getOrder).mockReturnValue(new Promise(() => {}));
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /looking up/i })).toBeDisabled();
    });

    await act(async () => {
      fireEvent.submit(
        screen.getByRole("button", { name: /looking up/i }).closest("form")!,
      );
    });

    expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(1);
  });
});

// ── Success: order details ────────────────────────────────────────────────────

describe("OrderLookupForm – order details", () => {
  beforeEach(() => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
  });

  it("renders order ID", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-order-id")).toHaveTextContent("AAPL-O-1");
    });
  });

  it("renders broker ID", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-broker-id")).toHaveTextContent("broker1");
    });
  });

  it("renders document number", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-document")).toHaveTextContent("DOC-001");
    });
  });

  it("renders side and symbol", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-side")).toHaveTextContent("ASK");
      expect(screen.getByTestId("detail-symbol")).toHaveTextContent("AAPL");
    });
  });

  it("formats price from integer cents to decimal with two places", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      // 15000 cents → 150.00
      expect(screen.getByTestId("detail-price")).toHaveTextContent("150.00");
    });
  });

  it("renders quantity, remaining, and filled", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-quantity")).toHaveTextContent("10");
      expect(screen.getByTestId("detail-remaining")).toHaveTextContent("10");
      expect(screen.getByTestId("detail-filled")).toHaveTextContent("0");
    });
  });

  it("renders status as a human-readable label for OPEN", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-status")).toHaveTextContent("Open");
    });
  });

  it("renders valid_until", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-valid-until")).toHaveTextContent(
        "2030-01-01T13:00:00.000Z",
      );
    });
  });

  it("renders No expiration (GTC) instead of raw null", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue({
      ...OPEN_ORDER,
      valid_until: null,
    });
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-valid-until")).toHaveTextContent(
        /no expiration/i,
      );
    });
    expect(screen.getByTestId("detail-valid-until")).not.toHaveTextContent("null");
  });

  it("renders client_order_id when present", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(ORDER_WITH_CLIENT_ID);
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByTestId("detail-client-order-id")).toHaveTextContent("my-ref-001");
    });
  });

  it("hides client_order_id row when null", async () => {
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.queryByTestId("detail-client-order-id")).not.toBeInTheDocument();
    });
  });
});

// ── Status labels ─────────────────────────────────────────────────────────────

describe("OrderLookupForm – status labels", () => {
  const statusCases: Array<[string, string]> = [
    ["OPEN", "Open"],
    ["PARTIALLY_FILLED", "Partially filled"],
    ["FILLED", "Filled"],
    ["CANCELED", "Canceled"],
    ["EXPIRED", "Expired"],
  ];

  for (const [apiStatus, label] of statusCases) {
    it(`shows "${label}" for status ${apiStatus}`, async () => {
      vi.mocked(apiClient.getOrder).mockResolvedValue({
        ...OPEN_ORDER,
        status: apiStatus as OrderResponse["status"],
      });
      renderForm();
      fillForm();
      await submitLookup();
      await waitFor(() => {
        expect(screen.getByTestId("detail-status")).toHaveTextContent(label);
      });
    });
  }
});

// ── Trades ────────────────────────────────────────────────────────────────────

describe("OrderLookupForm – trades", () => {
  it("shows no-trades message when trades array is empty", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByText(/no trades yet/i)).toBeInTheDocument();
    });
  });

  it("renders trades table when trades exist", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(ORDER_WITH_TRADES);
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("table", { name: /trades/i })).toBeInTheDocument();
      expect(screen.getByText("T-1")).toBeInTheDocument();
    });
  });

  it("formats trade price from cents to decimal", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(ORDER_WITH_TRADES);
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      // 15000 cents → 150.00 in the trades table
      const cells = screen.getAllByText("150.00");
      expect(cells.length).toBeGreaterThanOrEqual(1);
    });
  });
});

// ── Refresh button ────────────────────────────────────────────────────────────

describe("OrderLookupForm – manual refresh", () => {
  it("shows Refresh now button after first successful lookup", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
    });
  });

  it("calls getOrder again when Refresh now is clicked", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refresh now/i })).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /refresh now/i }));
    });

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);
    });
  });

  it("manual refresh works when auto-refresh is off", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("checkbox", { name: /auto-refresh/i })).not.toBeChecked();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /refresh now/i }));
    });

    await waitFor(() => {
      expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);
    });
  });

  it("disables Refresh now button while loading", async () => {
    vi.mocked(apiClient.getOrder)
      .mockResolvedValueOnce(OPEN_ORDER)
      .mockReturnValueOnce(new Promise(() => {}));

    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refresh now/i })).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /refresh now/i }));
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refreshing/i })).toBeDisabled();
    });
  });
});

// ── Auto-refresh toggle ───────────────────────────────────────────────────────

describe("OrderLookupForm – auto-refresh toggle", () => {
  it("auto-refresh toggle is off by default after first successful lookup", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("checkbox", { name: /auto-refresh/i })).not.toBeChecked();
    });
  });

  it("toggle is disabled for terminal statuses", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(FILLED_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByRole("checkbox", { name: /auto-refresh/i })).toBeDisabled();
    });
  });

  it("renders explanatory auto-refresh text after successful lookup", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(
        screen.getByText(/auto-refresh checks every 5 seconds/i),
      ).toBeInTheDocument();
    });
  });
});

// ── Last updated at ───────────────────────────────────────────────────────────

describe("OrderLookupForm – last updated at", () => {
  it("shows Last updated at after a successful fetch", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    await waitFor(() => {
      expect(screen.getByTestId("last-updated")).toBeInTheDocument();
      expect(screen.getByTestId("last-updated").textContent).toMatch(
        /last updated at/i,
      );
    });
  });

  it("does not show Last updated at before first fetch", () => {
    renderForm();
    expect(screen.queryByTestId("last-updated")).not.toBeInTheDocument();
  });
});

// ── Auto-refresh polling (fake timers) ────────────────────────────────────────
// Fake timers are activated AFTER the initial fetch so that waitFor (which uses
// setInterval internally) still works with real timers during setup.

describe("OrderLookupForm – polling (fake timers)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls every 5 seconds when auto-refresh is enabled", async () => {
    vi.mocked(apiClient.getOrder).mockResolvedValue(OPEN_ORDER);
    renderForm();
    fillForm();
    await submitLookup();

    // Wait for initial data using real timers
    await waitFor(() => {
      expect(screen.getByTestId("detail-order-id")).toBeInTheDocument();
    });

    // Switch to fake timers now that initial data is loaded
    vi.useFakeTimers();

    // Enable auto-refresh — TanStack Query schedules its next interval with fake timers
    await act(async () => {
      fireEvent.click(screen.getByRole("checkbox", { name: /auto-refresh/i }));
    });

    // Advance past the 5-second interval; advanceTimersByTimeAsync also drains microtasks
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);
  });

  it("stops polling once order reaches a terminal status", async () => {
    vi.mocked(apiClient.getOrder)
      .mockResolvedValueOnce(OPEN_ORDER)
      .mockResolvedValueOnce(FILLED_ORDER);

    renderForm();
    fillForm();
    await submitLookup();

    // Wait for initial OPEN status using real timers
    await waitFor(() => {
      expect(screen.getByTestId("detail-status")).toHaveTextContent("Open");
    });

    // Switch to fake timers
    vi.useFakeTimers();

    // Enable auto-refresh while order is non-terminal
    await act(async () => {
      fireEvent.click(screen.getByRole("checkbox", { name: /auto-refresh/i }));
    });

    // First poll at 5 s → FILLED order received (call #2)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);

    // Advance another 5 s — polling stopped, no further calls
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(vi.mocked(apiClient.getOrder)).toHaveBeenCalledTimes(2);
  });
});

// ── Error states ──────────────────────────────────────────────────────────────

describe("OrderLookupForm – errors", () => {
  it("shows 404 user-friendly message", async () => {
    vi.mocked(apiClient.getOrder).mockRejectedValue(
      new ApiClientError({ code: "ORDER_NOT_FOUND", message: "not found", status: 404 }),
    );
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Order not found for this broker/user.",
      );
    });
  });

  it("shows generic API error message", async () => {
    vi.mocked(apiClient.getOrder).mockRejectedValue(
      new ApiClientError({
        code: "GATEWAY_ERROR",
        message: "gateway error",
        status: 500,
      }),
    );
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("gateway error");
    });
  });

  it("shows network error message", async () => {
    vi.mocked(apiClient.getOrder).mockRejectedValue(
      new ApiClientError({
        code: "NETWORK_ERROR",
        message: "Failed to fetch",
        status: 0,
      }),
    );
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to fetch");
    });
  });

  it("shows generic message for unexpected (non-ApiClientError) errors", async () => {
    vi.mocked(apiClient.getOrder).mockRejectedValue(new Error("surprise"));
    renderForm();
    fillForm();
    await submitLookup();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    });
  });
});
