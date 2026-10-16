import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "../StatusBadge";

describe("StatusBadge", () => {
  it("shows an operational label when ok", () => {
    render(<StatusBadge ok />);
    expect(screen.getByText("Operational")).toBeInTheDocument();
  });

  it("shows an unavailable label when down", () => {
    render(<StatusBadge ok={false} />);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("accepts a custom label and hides the icon from assistive tech", () => {
    const { container } = render(<StatusBadge ok label="Connected" />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});
