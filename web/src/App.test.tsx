import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, it, expect } from "vitest";
import App from "./app/App";
import Layout from "./components/Layout";
import { routes } from "./app/routes";

function createTestQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: 0, gcTime: 0 } } });
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("App (browser router)", () => {
  it("renders and redirects root to the submit order page", async () => {
    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "Submit Order" }),
    ).toBeInTheDocument();
  });
});

describe("Navigation", () => {
  it("renders navigation links", () => {
    renderAt("/submit-order");
    expect(screen.getByRole("link", { name: "Submit Order" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Order Status" })).toBeInTheDocument();
  });

  it("renders Market navigation link", () => {
    renderAt("/submit-order");
    expect(screen.getByRole("link", { name: "Market" })).toBeInTheDocument();
  });

  it("has a main content landmark", () => {
    renderAt("/submit-order");
    expect(screen.getByRole("main")).toBeInTheDocument();
  });
});

describe("Root route", () => {
  it("redirects / to /submit-order and shows the submit order page", async () => {
    renderAt("/");
    expect(
      await screen.findByRole("heading", { name: "Submit Order" }),
    ).toBeInTheDocument();
  });
});

describe("SubmitOrderPage", () => {
  it("renders the Submit Order heading when navigated directly", () => {
    renderAt("/submit-order");
    expect(
      screen.getByRole("heading", { name: "Submit Order" }),
    ).toBeInTheDocument();
  });
});

describe("OrderStatusPage", () => {
  it("renders the Order Status heading", () => {
    renderAt("/status");
    expect(
      screen.getByRole("heading", { name: "Order Status" }),
    ).toBeInTheDocument();
  });
});

describe("MarketPage", () => {
  it("renders the Market Data heading when navigated to /market", () => {
    renderAt("/market");
    expect(screen.getByRole("heading", { name: /market data/i })).toBeInTheDocument();
  });
});

describe("Layout standalone", () => {
  it("renders nav with MemoryRouter", () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    );
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });
});
