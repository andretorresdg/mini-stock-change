import type { ApiError, OrderResponse, SubmitOrderRequest } from "./types";

// MVP defaults to local FastAPI.
// Deployed environments should set VITE_API_BASE_URL
// to the exact origin of the API server.
const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

class ApiClientError extends Error {
  readonly apiError: ApiError;

  constructor(apiError: ApiError) {
    super(apiError.message);
    this.name = "ApiClientError";
    this.apiError = apiError;
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return {
      code: "UNKNOWN_ERROR",
      message: response.statusText || "Unknown error",
      status: response.status,
    };
  }

  // FastAPI validation error shape: { detail: [{ msg, loc, type }] }
  if (
    body !== null &&
    typeof body === "object" &&
    "detail" in body &&
    Array.isArray((body as { detail: unknown }).detail)
  ) {
    const detail = (body as { detail: { msg: string }[] }).detail;
    const message = detail
      .map((d) => d.msg)
      .filter(Boolean)
      .join("; ");
    return {
      code: "VALIDATION_ERROR",
      message: message || "Validation error",
      status: response.status,
    };
  }

  // Standard backend ErrorResponse shape: { code, message }
  if (
    body !== null &&
    typeof body === "object" &&
    "code" in body &&
    "message" in body
  ) {
    const typed = body as { code: string; message: string };
    return {
      code: typed.code,
      message: typed.message,
      status: response.status,
    };
  }

  return {
    code: "UNKNOWN_ERROR",
    message: response.statusText || "Unknown error",
    status: response.status,
  };
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network request failed";
    const apiError: ApiError = {
      code: "NETWORK_ERROR",
      message,
      status: 0,
    };
    throw new ApiClientError(apiError);
  }

  if (!response.ok) {
    throw new ApiClientError(await parseErrorResponse(response));
  }

  return response.json() as Promise<T>;
}

export async function submitOrder(
  brokerId: string,
  req: SubmitOrderRequest,
): Promise<OrderResponse> {
  const path = `/api/v1/brokers/${encodeURIComponent(brokerId)}/orders`;
  return request<OrderResponse>("POST", path, req);
}

export async function getOrder(
  brokerId: string,
  orderId: string,
): Promise<OrderResponse> {
  const path = `/api/v1/brokers/${encodeURIComponent(brokerId)}/orders/${encodeURIComponent(orderId)}`;
  return request<OrderResponse>("GET", path);
}

export { ApiClientError, BASE_URL };
