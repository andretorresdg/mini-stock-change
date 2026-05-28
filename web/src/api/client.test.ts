import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, BASE_URL, getOrder, submitOrder } from "./client";
import type { OrderResponse, SubmitOrderRequest } from "./types";

const BROKER = "broker1";
const ORDER_ID = "AAPL-O-1";

const SAMPLE_ORDER: OrderResponse = {
  order_id: ORDER_ID,
  broker_id: BROKER,
  client_order_id: null,
  document_number: "DOC-001",
  side: "ASK",
  symbol: "AAPL",
  price: 150,
  quantity: 10,
  remaining_quantity: 10,
  filled_quantity: 0,
  status: "OPEN",
  valid_until: "2030-01-01T00:00:00Z",
  trades: [],
};

const SUBMIT_REQ: SubmitOrderRequest = {
  client_order_id: null,
  document_number: "DOC-001",
  side: "ASK",
  valid_until: "2030-01-01T00:00:00Z",
  symbol: "AAPL",
  price: 150,
  quantity: 10,
};

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? "OK" : "Error",
      json: () => Promise.resolve(body),
    }),
  );
}

function mockFetchNetworkFailure(message = "Failed to fetch"): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error(message)),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("BASE_URL", () => {
  it("defaults to http://localhost:8000", () => {
    expect(BASE_URL).toBe("http://localhost:8000");
  });
});

describe("submitOrder", () => {
  it("calls POST with correct URL and returns OrderResponse", async () => {
    mockFetch(201, SAMPLE_ORDER);

    const result = await submitOrder(BROKER, SUBMIT_REQ);

    expect(result).toEqual(SAMPLE_ORDER);
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${BASE_URL}/api/v1/brokers/broker1/orders`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual(SUBMIT_REQ);
  });

  it("encodes special characters in broker_id path segment", async () => {
    mockFetch(201, SAMPLE_ORDER);

    await submitOrder("broker/special", SUBMIT_REQ);

    const [url] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toContain("broker%2Fspecial");
  });

  it("sends Content-Type and Accept headers", async () => {
    mockFetch(201, SAMPLE_ORDER);

    await submitOrder(BROKER, SUBMIT_REQ);

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers["Accept"]).toBe("application/json");
  });
});

describe("getOrder", () => {
  it("calls GET with correct URL and returns OrderResponse", async () => {
    mockFetch(200, SAMPLE_ORDER);

    const result = await getOrder(BROKER, ORDER_ID);

    expect(result).toEqual(SAMPLE_ORDER);
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${BASE_URL}/api/v1/brokers/broker1/orders/AAPL-O-1`);
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
  });

  it("encodes special characters in order_id path segment", async () => {
    mockFetch(200, SAMPLE_ORDER);

    await getOrder(BROKER, "order/with spaces");

    const [url] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toContain("order%2Fwith%20spaces");
  });
});

describe("error handling — backend ErrorResponse", () => {
  it("throws ApiClientError with code and message from backend", async () => {
    mockFetch(404, { code: "ORDER_NOT_FOUND", message: "order not found" });

    await expect(getOrder(BROKER, ORDER_ID)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError &&
        e.apiError.code === "ORDER_NOT_FOUND" &&
        e.apiError.message === "order not found" &&
        e.apiError.status === 404,
    );
  });

  it("throws ApiClientError for 409 idempotency conflict", async () => {
    mockFetch(409, {
      code: "IDEMPOTENCY_CONFLICT",
      message: "conflict",
    });

    await expect(submitOrder(BROKER, SUBMIT_REQ)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError && e.apiError.status === 409,
    );
  });
});

describe("error handling — FastAPI validation error", () => {
  it("converts detail array into a readable VALIDATION_ERROR", async () => {
    mockFetch(422, {
      detail: [
        { msg: "value is not a valid integer", loc: ["body", "price"], type: "int_parsing" },
        { msg: "field required", loc: ["body", "symbol"], type: "missing" },
      ],
    });

    await expect(submitOrder(BROKER, SUBMIT_REQ)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError &&
        e.apiError.code === "VALIDATION_ERROR" &&
        e.apiError.message.includes("value is not a valid integer") &&
        e.apiError.message.includes("field required") &&
        e.apiError.status === 422,
    );
  });
});

describe("error handling — unparseable body", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.reject(new SyntaxError("not json")),
      }),
    );
  });

  it("falls back to statusText when body is not JSON", async () => {
    await expect(getOrder(BROKER, ORDER_ID)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError &&
        e.apiError.code === "UNKNOWN_ERROR" &&
        e.apiError.status === 500,
    );
  });
});

describe("error handling — unrecognised JSON body shape", () => {
  it("falls back to UNKNOWN_ERROR when body matches no known error shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: () => Promise.resolve({ error: "something unexpected" }),
      }),
    );

    await expect(getOrder(BROKER, ORDER_ID)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError &&
        e.apiError.code === "UNKNOWN_ERROR" &&
        e.apiError.status === 503,
    );
  });

  it("uses 'Unknown error' literal when statusText is empty and body unrecognised", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "",
        json: () => Promise.resolve({ error: "unexpected" }),
      }),
    );

    await expect(getOrder(BROKER, ORDER_ID)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError && e.apiError.message === "Unknown error",
    );
  });
});

describe("error handling — empty statusText on JSON parse failure", () => {
  it("uses 'Unknown error' literal when statusText is empty and JSON fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "",
        json: () => Promise.reject(new SyntaxError("bad json")),
      }),
    );

    await expect(getOrder(BROKER, ORDER_ID)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError && e.apiError.message === "Unknown error",
    );
  });
});

describe("error handling — FastAPI validation with empty msg fields", () => {
  it("falls back to 'Validation error' when all detail msgs are empty", async () => {
    mockFetch(422, {
      detail: [{ msg: "", loc: ["body", "price"], type: "int_parsing" }],
    });

    await expect(submitOrder(BROKER, SUBMIT_REQ)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError && e.apiError.message === "Validation error",
    );
  });
});

describe("error handling — network failure", () => {
  it("wraps network errors as NETWORK_ERROR with status 0", async () => {
    mockFetchNetworkFailure("Failed to fetch");

    await expect(submitOrder(BROKER, SUBMIT_REQ)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError &&
        e.apiError.code === "NETWORK_ERROR" &&
        e.apiError.status === 0 &&
        e.apiError.message === "Failed to fetch",
    );
  });

  it("handles non-Error network throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue("string error"));

    await expect(submitOrder(BROKER, SUBMIT_REQ)).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof ApiClientError && e.apiError.code === "NETWORK_ERROR",
    );
  });
});
