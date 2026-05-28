import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SubmitOrderForm from "./SubmitOrderForm";

function renderForm(isPending = false) {
  render(<SubmitOrderForm isPending={isPending} />);
}

/** Fill every required field with a valid value. */
function fillValidForm() {
  fireEvent.change(screen.getByLabelText(/broker \/ username/i), {
    target: { value: "broker1" },
  });
  fireEvent.blur(screen.getByLabelText(/broker \/ username/i));

  fireEvent.change(screen.getByLabelText(/document number/i), {
    target: { value: "DOC-001" },
  });
  fireEvent.blur(screen.getByLabelText(/document number/i));

  fireEvent.change(screen.getByLabelText(/stock symbol/i), {
    target: { value: "AAPL" },
  });

  fireEvent.change(screen.getByLabelText(/unit price/i), {
    target: { value: "10.50" },
  });
  fireEvent.blur(screen.getByLabelText(/unit price/i));

  fireEvent.change(screen.getByLabelText(/quantity/i), {
    target: { value: "5" },
  });
}

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

// ── Broker ID behaviour ───────────────────────────────────────────────────────

describe("SubmitOrderForm – broker ID validation", () => {
  it("shows broker ID validation error when field is blurred while empty", () => {
    renderForm();
    fireEvent.blur(screen.getByLabelText(/broker \/ username/i));
    expect(screen.getByText(/broker id must not be empty/i)).toBeInTheDocument();
  });
});

// ── Document number behaviour ─────────────────────────────────────────────────

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

  it("is disabled when isPending is true even if the form is valid", () => {
    renderForm(true);
    fillValidForm();
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });

  it("is disabled after entering an invalid symbol", () => {
    renderForm();
    fillValidForm();
    // override symbol with invalid value
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "1" },
    });
    expect(screen.getByRole("button", { name: /submit order/i })).toBeDisabled();
  });

  it("can be submitted when the form is valid (form submit event handled)", () => {
    renderForm();
    fillValidForm();
    const form = screen.getByRole("button", { name: /submit order/i }).closest("form")!;
    // Should not throw; handleSubmit calls e.preventDefault() and returns.
    expect(() => fireEvent.submit(form)).not.toThrow();
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
    // "." passes sanitize but normalizePriceDisplay(".") returns "" so preview shows "—"
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
    // clientOrderId is left empty — button should still be enabled
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
