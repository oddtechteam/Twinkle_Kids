import { expect, test } from "@playwright/test";

test("homepage renders the Twinkle Kids shell", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Twinkle Kids/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Cute Styles for Little Smiles");
  await expect(page.getByRole("link", { name: "Twinkle Kids home" }).first()).toBeVisible();
});

test("status page reports the storefront and API", async ({ page }) => {
  await page.goto("/status");
  await expect(page.getByRole("heading", { name: "System status" })).toBeVisible();
  await expect(page.getByText("Storefront (Next.js)")).toBeVisible();
  // Passes whether or not the API is running; the row must resolve out of its loading state.
  await expect(page.getByText(/^API/).first()).toBeVisible();
});

test("page does not scroll horizontally", async ({ page }) => {
  await page.goto("/");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
