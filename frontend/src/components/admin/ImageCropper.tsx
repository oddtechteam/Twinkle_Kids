"use client";

import { Crop, Move, RotateCcw, Trash2, ZoomIn, ZoomOut } from "lucide-react";
import {
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation } from "@/lib/admin/hooks";
import type { CropRect, MediaAsset } from "@/lib/admin/types";
import { FRAMES, type ImageFrame, frameRatio } from "@/lib/media/frames";
import styles from "./ImageCropper.module.css";

const MAX_ZOOM = 5;
/** Below this many source pixels across, the crop will look soft on a large card. */
const SOFT_WIDTH = 640;

interface Size {
  width: number;
  height: number;
}

/** Zoom 1 = the frame covers the whole image on its tighter side; cx/cy = centre (0-1). */
interface View {
  zoom: number;
  cx: number;
  cy: number;
}

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

/** The crop rectangle (fractions of the original) for a view: depends only on aspect ratios. */
function rectFor(view: View, natural: Size, ratio: number): CropRect {
  const width = Math.min(1, (ratio * natural.height) / natural.width) / view.zoom;
  const height = Math.min(1, natural.width / (ratio * natural.height)) / view.zoom;
  return {
    x: clamp(view.cx - width / 2, 0, 1 - width),
    y: clamp(view.cy - height / 2, 0, 1 - height),
    width,
    height,
  };
}

/** Keep the centre where the rectangle can actually be, so dragging past an edge doesn't stick. */
function settle(view: View, natural: Size, ratio: number): View {
  const zoom = clamp(view.zoom, 1, MAX_ZOOM);
  const rect = rectFor({ ...view, zoom }, natural, ratio);
  return { zoom, cx: rect.x + rect.width / 2, cy: rect.y + rect.height / 2 };
}

function viewFromRect(rect: CropRect, natural: Size, ratio: number): View {
  const fullWidth = Math.min(1, (ratio * natural.height) / natural.width);
  return settle(
    { zoom: fullWidth / rect.width, cx: rect.x + rect.width / 2, cy: rect.y + rect.height / 2 },
    natural,
    ratio,
  );
}

/** Shows `rect` of the image filling a frame of the given ratio. Pure CSS: any size works. */
export function CropFrame({
  src,
  rect,
  frame,
  className,
  children,
  onLoad,
}: {
  src: string;
  rect: CropRect | null;
  frame: ImageFrame;
  className?: string;
  children?: ReactNode;
  onLoad?: (size: Size) => void;
}) {
  const imageStyle: CSSProperties = rect
    ? {
        width: `${100 / rect.width}%`,
        height: `${100 / rect.height}%`,
        left: `${(-rect.x / rect.width) * 100}%`,
        top: `${(-rect.y / rect.height) * 100}%`,
      }
    : { inset: 0, width: "100%", height: "100%", objectFit: "cover" };
  return (
    <div className={`${styles.frame} ${className ?? ""}`} style={{ aspectRatio: frameRatio(frame) }}>
      {/* A plain <img>: the editor needs the untouched original at its natural size. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        draggable={false}
        className={styles.frameImage}
        style={imageStyle}
        onLoad={(e) => onLoad?.({ width: e.currentTarget.naturalWidth, height: e.currentTarget.naturalHeight })}
      />
      {children}
    </div>
  );
}

/**
 * Social-media-style crop editor: drag to reposition, zoom with the slider, wheel or pinch,
 * and see the storefront previews update live. Saving sends only the rectangle; the server cuts
 * it from the kept original, so the crop can be edited again at any time.
 */
export function ImageCropDialog({
  open,
  asset,
  frame,
  onClose,
  onSaved,
}: {
  open: boolean;
  asset: MediaAsset;
  frame: ImageFrame;
  onClose: () => void;
  onSaved: (asset: MediaAsset) => void;
}) {
  const spec = FRAMES[frame];
  const ratio = spec.ratioWidth / spec.ratioHeight;
  const saved = asset.crops?.[frame] ?? null;
  const [natural, setNatural] = useState<Size | null>(null);
  const [view, setView] = useState<View>({ zoom: 1, cx: 0.5, cy: 0.5 });
  const [dragging, setDragging] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<{ view: View; x: number; y: number; distance: number } | null>(null);
  const { run, pending } = useMutation();

  const rect = natural ? rectFor(view, natural, ratio) : null;

  const update = useCallback(
    (next: (current: View) => View) => {
      if (!natural) return;
      setView((current) => settle(next(current), natural, ratio));
    },
    [natural, ratio],
  );

  const handleLoad = (size: Size) => {
    if (natural) return;
    setNatural(size);
    setView(saved ? viewFromRect(saved, size, ratio) : { zoom: 1, cx: 0.5, cy: 0.5 });
  };

  // Wheel zoom needs a non-passive listener to stop the dialog from scrolling.
  useEffect(() => {
    const element = viewport.current;
    if (!element || !open) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      update((v) => ({ ...v, zoom: v.zoom * Math.exp(-event.deltaY * 0.0015) }));
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, [open, update, natural]);

  const spread = () => {
    const [a, b] = [...pointers.current.values()];
    return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
  };

  const startGesture = () => {
    const points = [...pointers.current.values()];
    const x = points.reduce((sum, p) => sum + p.x, 0) / points.length;
    const y = points.reduce((sum, p) => sum + p.y, 0) / points.length;
    gesture.current = { view, x, y, distance: spread() };
  };

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!natural) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    startGesture();
    setDragging(true);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(event.pointerId) || !gesture.current || !rect || !viewport.current) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const points = [...pointers.current.values()];
    const x = points.reduce((sum, p) => sum + p.x, 0) / points.length;
    const y = points.reduce((sum, p) => sum + p.y, 0) / points.length;
    const start = gesture.current;
    const box = viewport.current.getBoundingClientRect();
    const zoom = start.distance > 0 ? start.view.zoom * (spread() / start.distance) : start.view.zoom;
    const startRect = rectFor(start.view, natural!, ratio);
    // Pixels on screen -> fractions of the image at the gesture's starting scale.
    const imageWidth = box.width / startRect.width;
    const imageHeight = box.height / startRect.height;
    update(() => ({
      zoom,
      cx: start.view.cx - (x - start.x) / imageWidth,
      cy: start.view.cy - (y - start.y) / imageHeight,
    }));
  };

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    pointers.current.delete(event.pointerId);
    if (pointers.current.size > 0) startGesture();
    else {
      gesture.current = null;
      setDragging(false);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!rect) return;
    const step = event.shiftKey ? 0.1 : 0.02;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step * rect.width, 0],
      ArrowRight: [step * rect.width, 0],
      ArrowUp: [0, -step * rect.height],
      ArrowDown: [0, step * rect.height],
    };
    const move = moves[event.key];
    if (move) {
      event.preventDefault();
      update((v) => ({ ...v, cx: v.cx + move[0], cy: v.cy + move[1] }));
    } else if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      update((v) => ({ ...v, zoom: v.zoom * 1.1 }));
    } else if (event.key === "-") {
      event.preventDefault();
      update((v) => ({ ...v, zoom: v.zoom / 1.1 }));
    }
  };

  const save = async () => {
    if (!rect) return;
    const res = await run(() => adminApi.saveCrop(asset.id, frame, rect), { success: `${spec.label} crop saved` });
    if (res.ok) {
      onSaved(res.result);
      onClose();
    }
  };

  const removeSaved = async () => {
    const res = await run(() => adminApi.removeCrop(asset.id, frame), { success: "Crop removed — the image is centred automatically" });
    if (res.ok) {
      onSaved(res.result);
      onClose();
    }
  };

  const sourceWidth = rect && natural ? Math.round(rect.width * natural.width) : null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Crop for ${spec.label.toLowerCase()} (${spec.ratioWidth}:${spec.ratioHeight})`}
      description={`${spec.usage}. The original file is kept, so you can change this later.`}
      className={styles.dialog}
      footer={
        <div className={styles.footer}>
          {saved && (
            <Button variant="ghost" size="sm" iconStart={<Trash2 aria-hidden="true" />} disabled={pending} onClick={removeSaved}>
              Remove crop
            </Button>
          )}
          <span className={styles.spacer} />
          <Button variant="outline" onClick={onClose} disabled={pending}>
            Cancel
          </Button>
          <Button iconStart={<Crop aria-hidden="true" />} loading={pending} disabled={!rect} onClick={save}>
            Save crop
          </Button>
        </div>
      }
    >
      <div className={styles.layout}>
        <div className={styles.editor}>
          <div
            ref={viewport}
            className={`${styles.viewport} ${dragging ? styles.dragging : ""}`}
            style={{ "--frame-ratio": ratio } as CSSProperties}
            tabIndex={0}
            role="group"
            aria-label="Crop area. Drag or use the arrow keys to reposition; plus and minus keys zoom."
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            onKeyDown={onKeyDown}
          >
            <CropFrame src={asset.url} rect={rect} frame={frame} onLoad={handleLoad} className={styles.stage}>
              <span className={styles.grid} aria-hidden="true" />
            </CropFrame>
            {!natural && <span className={styles.loading}>Loading original…</span>}
          </div>
          <div className={styles.controls}>
            <button
              type="button"
              className={styles.iconButton}
              aria-label="Zoom out"
              disabled={!natural || view.zoom <= 1}
              onClick={() => update((v) => ({ ...v, zoom: v.zoom / 1.2 }))}
            >
              <ZoomOut size={18} aria-hidden="true" />
            </button>
            <input
              type="range"
              className={styles.slider}
              min={1}
              max={MAX_ZOOM}
              step={0.01}
              value={view.zoom}
              disabled={!natural}
              aria-label="Zoom"
              onChange={(e) => {
                const zoom = Number(e.target.value);
                update((v) => ({ ...v, zoom }));
              }}
            />
            <button
              type="button"
              className={styles.iconButton}
              aria-label="Zoom in"
              disabled={!natural || view.zoom >= MAX_ZOOM}
              onClick={() => update((v) => ({ ...v, zoom: v.zoom * 1.2 }))}
            >
              <ZoomIn size={18} aria-hidden="true" />
            </button>
            <button
              type="button"
              className={styles.iconButton}
              aria-label="Reset to centred"
              title="Reset to centred"
              disabled={!natural}
              onClick={() => update(() => ({ zoom: 1, cx: 0.5, cy: 0.5 }))}
            >
              <RotateCcw size={18} aria-hidden="true" />
            </button>
          </div>
          <p className={styles.hint}>
            <Move size={14} aria-hidden="true" /> Drag to reposition · scroll, pinch or use the slider to zoom
          </p>
        </div>

        <aside className={styles.previews} aria-label="Live preview">
          <span className={styles.previewLabel}>Live preview</span>
          <div className={styles.previewRow}>
            <figure className={styles.previewCard}>
              <CropFrame src={asset.url} rect={rect} frame={frame} className={`${styles.previewLarge} ${styles[frame] ?? ""}`} />
              <figcaption>Storefront card</figcaption>
            </figure>
            <figure className={styles.previewCard}>
              <CropFrame src={asset.url} rect={rect} frame={frame} className={`${styles.previewSmall} ${styles[frame] ?? ""}`} />
              <figcaption>Small screens</figcaption>
            </figure>
          </div>
          {sourceWidth !== null && (
            <p className={sourceWidth < SOFT_WIDTH ? styles.warning : styles.hint}>
              {sourceWidth < SOFT_WIDTH
                ? `Only ${sourceWidth}px of the original is used — this may look soft. Zoom out or upload a larger photo.`
                : `Uses ${sourceWidth}×${Math.round(sourceWidth / ratio)}px of the ${natural!.width}×${natural!.height}px original.`}
            </p>
          )}
          {saved && <p className={styles.hint}>A crop is saved for this frame; saving again replaces it.</p>}
        </aside>
      </div>
    </Dialog>
  );
}
