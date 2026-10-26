/**
 * Storefront image frames: every card in a section shares one frame, so an image cropped for a
 * frame shows the same composition wherever it appears. Mirrors FRAME_SPECS in
 * backend/app/domain/entities/media.py (the server snaps every crop to these ratios).
 */

export type ImageFrame = "product" | "category" | "collection" | "hero" | "banner";

export interface FrameSpec {
  label: string;
  /** Where the frame is used, shown in the crop editor. */
  usage: string;
  ratioWidth: number;
  ratioHeight: number;
}

export const FRAMES: Record<ImageFrame, FrameSpec> = {
  product: { label: "Product", usage: "Product cards, product gallery and bag", ratioWidth: 4, ratioHeight: 5 },
  category: { label: "Category", usage: "Category tiles", ratioWidth: 1, ratioHeight: 1 },
  collection: { label: "Collection", usage: "Featured collection tiles", ratioWidth: 3, ratioHeight: 4 },
  hero: { label: "Hero", usage: "Homepage hero arch (desktop and mobile)", ratioWidth: 8, ratioHeight: 15 },
  banner: { label: "Banner", usage: "Promo banner and occasion photos", ratioWidth: 4, ratioHeight: 5 },
};

export const FRAME_NAMES = Object.keys(FRAMES) as ImageFrame[];

/** CSS aspect-ratio for a frame, e.g. "4 / 5". */
export const frameRatio = (frame: ImageFrame) => `${FRAMES[frame].ratioWidth} / ${FRAMES[frame].ratioHeight}`;

export interface FramedImage {
  url: string;
  width: number;
  height: number;
}

/**
 * The admin-cropped rendition for `frame` when one exists, else the original (which the
 * storefront then centres with `object-fit: cover`).
 */
export function framedImage<T extends FramedImage & { crops?: Partial<Record<string, FramedImage>> }>(
  image: T,
  frame: ImageFrame,
): FramedImage {
  return image.crops?.[frame] ?? { url: image.url, width: image.width, height: image.height };
}
