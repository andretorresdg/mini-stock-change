import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the Mini Exchange heading", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Mini Exchange" })).toBeInTheDocument();
  });

  it("renders the MVP subtitle", () => {
    render(<App />);
    expect(screen.getByText("In-memory MVP trading interface")).toBeInTheDocument();
  });
});
