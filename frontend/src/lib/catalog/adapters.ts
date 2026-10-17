import type { Money, Price, ProductDetail, ProductImage, ProductSummary } from "@/lib/api/types";

/** The minimal shape a product card renders, regardless of which endpoint supplied it. */
export interface CardProduct {
  slug: string;
  name: string;
  price: Price;
  fromPrice?: Money;
  priceVaries: boolean;
  inStock: boolean;
  image: ProductImage | null;
  badges: string[];
}

export function cardFromSummary(product: ProductSummary): CardProduct {
  return {
    slug: product.slug,
    name: product.name,
    price: product.price,
    fromPrice: product.from_price,
    priceVaries: product.price_varies,
    inStock: product.in_stock,
    image: product.primary_image,
    badges: product.badges ?? [],
  };
}

export function cardFromDetail(product: ProductDetail): CardProduct {
  const sellings = new Set(product.variants.map((v) => v.price.selling_price));
  return {
    slug: product.slug,
    name: product.name,
    price: product.price,
    priceVaries: sellings.size > 1,
    inStock: product.in_stock,
    image: product.images[0] ?? null,
    badges: product.badges ?? [],
  };
}

/** Only absolute http(s) URLs are rendered with next/image (others fall back to illustration). */
export function isRenderableImage(url: string | undefined | null): url is string {
  return typeof url === "string" && /^https?:\/\//.test(url);
}
