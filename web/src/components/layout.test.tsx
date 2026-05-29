import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EmptyState from "./EmptyState";
import Panel from "./Panel";
import TwoColumnPage from "./TwoColumnPage";

describe("TwoColumnPage", () => {
  it("renders left and right column content", () => {
    render(
      <TwoColumnPage
        left={<p>Left controls</p>}
        right={<p>Right results</p>}
      />,
    );

    expect(screen.getByText("Left controls")).toBeInTheDocument();
    expect(screen.getByText("Right results")).toBeInTheDocument();
  });

  it("uses two-column layout containers", () => {
    const { container } = render(
      <TwoColumnPage left={<span>Left</span>} right={<span>Right</span>} />,
    );

    expect(container.querySelector(".two-column-page")).toBeInTheDocument();
    expect(container.querySelector(".page-column--left")).toBeInTheDocument();
    expect(container.querySelector(".page-column--right")).toBeInTheDocument();
  });
});

describe("Panel", () => {
  it("renders a titled region", () => {
    render(
      <Panel title="Order preview" titleId="previewHeading">
        <p>Preview content</p>
      </Panel>,
    );

    expect(screen.getByRole("region", { name: /order preview/i })).toBeInTheDocument();
    expect(screen.getByText("Preview content")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders status text for screen readers", () => {
    render(<EmptyState>Enter details to continue.</EmptyState>);

    expect(screen.getByRole("status")).toHaveTextContent("Enter details to continue.");
  });
});
