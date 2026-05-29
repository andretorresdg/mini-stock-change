import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as apiClient from "../../api/client";
import { ApiClientError } from "../../api/client";
import type { BookSnapshotResponse, MarketTradesResponse } from "../../api/types";
import MarketView from "./MarketView";

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return { ...actual, getBookSnapshot: vi.fn(), getMarketTrades: vi.fn() };
});

const MOCK_BOOK: BookSnapshotResponse = {
  symbol: "AAPL",
  bids: [{ price: 1000, quantity: 100 }],
  asks: [{ price: 2000, quantity: 50 }],
};

const MOCK_TRADES: MarketTradesResponse = {
  symbol: "AAPL",
  trades: [
    { trade_id: "AAPL-T-1", sequence: 1, symbol: "AAPL", price: 1500, quantity: 75 },
  ],
};

const EMPTY_BOOK: BookSnapshotResponse = { symbol: "AAPL", bids: [], asks: [] };
const EMPTY_TRADES: MarketTradesResponse = { symbol: "AAPL", trades: [] };

afterEach(() => {
  vi.resetAllMocks();
});

function renderMarket() {
  render(<MarketView />);
}

function typeSymbol(value: string) {
  fireEvent.change(screen.getByLabelText(/symbol/i), { target: { value } });
}

async function loadSuccessfully() {
  vi.mocked(apiClient.getBookSnapshot).mockResolvedValue(MOCK_BOOK);
  vi.mocked(apiClient.getMarketTrades).mockResolvedValue(MOCK_TRADES);
  typeSymbol("AAPL");
  fireEvent.click(screen.getByRole("button"));
  await waitFor(() =>
    expect(screen.getByRole("heading", { name: /^bids$/i })).toBeInTheDocument(),
  );
}

describe("MarketView – initial rendering", () => {
  it("renders symbol input", () => {
    renderMarket();
    expect(screen.getByLabelText(/symbol/i)).toBeInTheDocument();
  });

  it("renders book depth input with default value 10", () => {
    renderMarket();
    expect(screen.getByLabelText(/book depth/i)).toHaveValue(10);
  });

  it("renders trade limit input with default value 20", () => {
    renderMarket();
    expect(screen.getByLabelText(/trade limit/i)).toHaveValue(20);
  });

  it("renders load button disabled when symbol is empty", () => {
    renderMarket();
    expect(screen.getByRole("button", { name: /load market data/i })).toBeDisabled();
  });

  it("shows empty state before loading market data", () => {
    renderMarket();
    expect(
      screen.getByText(/load a symbol to view the current book and recent trades/i),
    ).toBeInTheDocument();
  });
});

describe("MarketView – symbol input", () => {
  it("uppercases lowercase input automatically", () => {
    renderMarket();
    typeSymbol("aapl");
    expect(screen.getByLabelText(/symbol/i)).toHaveValue("AAPL");
  });

  it("strips non-letter characters from symbol input", () => {
    renderMarket();
    typeSymbol("A1B2");
    expect(screen.getByLabelText(/symbol/i)).toHaveValue("AB");
  });

  it("valid symbol enables the load button", () => {
    renderMarket();
    typeSymbol("AAPL");
    expect(screen.getByRole("button", { name: /load market data/i })).not.toBeDisabled();
  });

  it("empty symbol keeps load button disabled", () => {
    renderMarket();
    typeSymbol("");
    expect(screen.getByRole("button", { name: /load market data/i })).toBeDisabled();
  });

  it("changing book depth updates the input value", () => {
    renderMarket();
    fireEvent.change(screen.getByLabelText(/book depth/i), { target: { value: "5" } });
    expect(screen.getByLabelText(/book depth/i)).toHaveValue(5);
  });

  it("changing trade limit updates the input value", () => {
    renderMarket();
    fireEvent.change(screen.getByLabelText(/trade limit/i), { target: { value: "30" } });
    expect(screen.getByLabelText(/trade limit/i)).toHaveValue(30);
  });
});

describe("MarketView – load behavior", () => {
  it("calls both API methods with depth and limit on load", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockResolvedValue(MOCK_BOOK);
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(MOCK_TRADES);

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(vi.mocked(apiClient.getBookSnapshot)).toHaveBeenCalledWith("AAPL", 10);
      expect(vi.mocked(apiClient.getMarketTrades)).toHaveBeenCalledWith("AAPL", 20);
    });
  });

  it("falls back to depth=10 when depth input is cleared", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockResolvedValue(MOCK_BOOK);
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(MOCK_TRADES);

    renderMarket();
    fireEvent.change(screen.getByLabelText(/book depth/i), { target: { value: "" } });
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(vi.mocked(apiClient.getBookSnapshot)).toHaveBeenCalledWith("AAPL", 10),
    );
  });

  it("falls back to limit=20 when limit input is cleared", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockResolvedValue(MOCK_BOOK);
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(MOCK_TRADES);

    renderMarket();
    fireEvent.change(screen.getByLabelText(/trade limit/i), { target: { value: "" } });
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(vi.mocked(apiClient.getMarketTrades)).toHaveBeenCalledWith("AAPL", 20),
    );
  });

  it("shows loading text while fetch is pending", () => {
    vi.mocked(apiClient.getBookSnapshot).mockReturnValue(new Promise(() => {}));
    vi.mocked(apiClient.getMarketTrades).mockReturnValue(new Promise(() => {}));

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("disables button while loading", () => {
    vi.mocked(apiClient.getBookSnapshot).mockReturnValue(new Promise(() => {}));
    vi.mocked(apiClient.getMarketTrades).mockReturnValue(new Promise(() => {}));

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("button")).toBeDisabled();
  });
});

describe("MarketView – success state", () => {
  it("renders Bids heading and bid price as decimal", async () => {
    renderMarket();
    await loadSuccessfully();

    expect(screen.getByRole("heading", { name: /^bids$/i })).toBeInTheDocument();
    expect(screen.getByText("10.00")).toBeInTheDocument();
  });

  it("renders Asks heading and ask price as decimal", async () => {
    renderMarket();
    await loadSuccessfully();

    expect(screen.getByRole("heading", { name: /^asks$/i })).toBeInTheDocument();
    expect(screen.getByText("20.00")).toBeInTheDocument();
  });

  it("renders Recent Trades heading and trade data", async () => {
    renderMarket();
    await loadSuccessfully();

    expect(screen.getByRole("heading", { name: /recent trades/i })).toBeInTheDocument();
    expect(screen.getByText("AAPL-T-1")).toBeInTheDocument();
    expect(screen.getByText("15.00")).toBeInTheDocument();
  });

  it("formats integer cents as decimal money with two decimal places", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockResolvedValue({
      symbol: "AAPL",
      bids: [{ price: 9999, quantity: 1 }],
      asks: [],
    });
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(EMPTY_TRADES);

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByText("99.99")).toBeInTheDocument());
  });

  it("shows Refresh button label after first successful load", async () => {
    renderMarket();
    await loadSuccessfully();

    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });
});

describe("MarketView – empty states", () => {
  it("shows no-bids, no-asks and no-trades messages for an empty book", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockResolvedValue(EMPTY_BOOK);
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(EMPTY_TRADES);

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByText(/no bids/i)).toBeInTheDocument());
    expect(screen.getByText(/no asks/i)).toBeInTheDocument();
    expect(screen.getByText(/no trades/i)).toBeInTheDocument();
  });
});

describe("MarketView – error state", () => {
  it("shows error message when API call fails", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockRejectedValue(
      new ApiClientError({ code: "NETWORK_ERROR", message: "Network failure", status: 0 }),
    );
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(EMPTY_TRADES);

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/Network failure/i),
    );
  });

  it("shows generic message for non-ApiClientError throws", async () => {
    vi.mocked(apiClient.getBookSnapshot).mockRejectedValue(new Error("unexpected"));
    vi.mocked(apiClient.getMarketTrades).mockResolvedValue(EMPTY_TRADES);

    renderMarket();
    typeSymbol("AAPL");
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/Failed to load market data/i),
    );
  });
});

describe("MarketView – manual refresh", () => {
  it("clicking Refresh calls both API methods a second time", async () => {
    renderMarket();
    await loadSuccessfully();

    const refreshBtn = screen.getByRole("button", { name: /refresh/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(vi.mocked(apiClient.getBookSnapshot)).toHaveBeenCalledTimes(2);
      expect(vi.mocked(apiClient.getMarketTrades)).toHaveBeenCalledTimes(2);
    });
  });
});
