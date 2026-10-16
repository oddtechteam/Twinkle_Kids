import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteHeader } from "../SiteHeader";

describe("SiteHeader", () => {
  it("links the logo home and labels every icon action", () => {
    render(<SiteHeader />);
    expect(screen.getByRole("link", { name: "Twinkle Kids home" })).toHaveAttribute("href", "/");
    for (const name of ["Search", "Wishlist", "Account", "Shopping bag"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });
});
