/**
 * Static fallbacks used only until the Site Settings API exists (Phase 5).
 * Routine content (banners, categories, products, contact details) must come from the API,
 * not from this file.
 */
export const siteFallback = {
  name: "Twinkle Kids",
  tagline: "Cute Styles for Little Smiles.",
  description:
    "Premium children's clothing boutique — thoughtfully made outfits for little ones.",
} as const;
