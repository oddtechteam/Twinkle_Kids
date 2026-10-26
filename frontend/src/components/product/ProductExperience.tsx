"use client";

import { useRouter } from "next/navigation";
import { MessageCircle, Ruler, ShoppingBag, Zap } from "lucide-react";
import { type ReactNode, useId, useMemo, useState } from "react";

import { useNavigationProgress } from "@/components/layout/NavigationProgress";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { ChoiceChip, ColourSwatch } from "@/components/ui/Form";
import { Icon } from "@/components/ui/Icon";
import { Price } from "@/components/ui/Price";
import { QuantityStepper } from "@/components/ui/QuantityStepper";
import { useToast } from "@/components/ui/Toast";
import type { ProductDetail, ProductVariant } from "@/lib/api/types";
import { useBag } from "@/lib/bag/BagProvider";
import type { IconName } from "@/lib/content/types";
import { useWhatsAppOrder } from "@/components/whatsapp/WhatsAppHandoff";
import { ProductGallery } from "./ProductGallery";
import { WishlistButton } from "./WishlistButton";
import styles from "./ProductExperience.module.css";

interface Props {
  product: ProductDetail;
  /** Store setting: "Order on WhatsApp" is offered only when enabled with a number. */
  whatsappEnabled: boolean;
  eyebrow?: ReactNode;
  /** Server-rendered description and details. */
  details: ReactNode;
}

/** Gallery + purchase panel sharing the selected colour/size. Prices come from the variant's PriceView. */
export function ProductExperience({ product, whatsappEnabled, eyebrow, details }: Props) {
  const variants = product.variants.filter((v) => v.is_active);
  const hasColours = product.colours.length > 0;
  const hasSizes = product.sizes.length > 0;

  const firstAvailableColour =
    product.colours.find((c) => variants.some((v) => v.colour === c && v.in_stock)) ?? product.colours[0] ?? null;
  const [colour, setColour] = useState<string | null>(hasColours ? firstAvailableColour : null);
  const [size, setSize] = useState<string | null>(product.sizes.length === 1 ? (product.sizes[0] ?? null) : null);
  const [showSizeError, setShowSizeError] = useState(false);
  const [sizeChartOpen, setSizeChartOpen] = useState(false);
  const [quantity, setQuantity] = useState(1);
  const [busy, setBusy] = useState<"bag" | "buy" | "whatsapp" | null>(null);

  const bag = useBag();
  const toast = useToast();
  const router = useRouter();
  const progress = useNavigationProgress();
  const whatsapp = useWhatsAppOrder();
  const sizeGroup = useId();
  const colourGroup = useId();
  const errorId = useId();

  const matches = (v: ProductVariant, c: string | null, s: string | null) =>
    (!hasColours || v.colour === c) && (!hasSizes || v.size === s);

  const selected = useMemo(() => {
    const complete = (!hasColours || colour !== null) && (!hasSizes || size !== null);
    return complete ? (variants.find((v) => matches(v, colour, size)) ?? null) : null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [colour, size, product.slug]);

  const priceVaries = new Set(variants.map((v) => v.price.selling_price)).size > 1;
  const lowest = variants.reduce<string | undefined>(
    (min, v) => (min === undefined || Number(v.price.selling_price) < Number(min) ? v.price.selling_price : min),
    undefined,
  );

  const sizeInStock = (s: string) => variants.some((v) => v.size === s && (!hasColours || v.colour === colour) && v.in_stock);
  const colourInStock = (c: string) => variants.some((v) => v.colour === c && v.in_stock);
  const colourHex = (c: string) => variants.find((v) => v.colour === c)?.colour_hex ?? null;
  const focusVariantIds = colour ? variants.filter((v) => v.colour === colour).map((v) => v.id) : [];
  const chart = product.size_chart;
  const chartUsable = Boolean(chart?.columns?.length && chart?.rows?.length);

  const notes: { icon: IconName; text: string }[] = [
    ...(chartUsable ? [{ icon: "ruler" as const, text: "Check the size guide for the best fit" }] : []),
    ...(whatsappEnabled ? [{ icon: "message-circle" as const, text: "Prefer to chat? Order on WhatsApp" }] : []),
  ];

  /** The chosen variant, or null after prompting the shopper to finish choosing. */
  function requireSelection(): ProductVariant | null {
    if (!selected) {
      setShowSizeError(true);
      return null;
    }
    return selected;
  }

  async function addToBag(then?: "checkout") {
    const variant = requireSelection();
    if (!variant) return;
    setBusy(then ? "buy" : "bag");
    const result = await bag.add(variant.id, quantity);
    setBusy(null);
    if (!result.ok) {
      toast.show({ tone: "warning", title: "Couldn't add to your bag", description: result.message });
      return;
    }
    if (then === "checkout") {
      progress.start("/bag");
      router.push("/bag");
      return;
    }
    toast.show({
      title: "Added to your bag",
      description: `${quantity} × ${product.name}${variantLabel(variant) ? ` (${variantLabel(variant)})` : ""}`,
    });
  }

  async function orderOnWhatsApp() {
    const variant = requireSelection();
    if (!variant) return;
    await whatsapp.start([{ variantId: variant.id, quantity }]);
  }

  // Nothing purchasable at all, or the chosen option is out of stock.
  const soldOut = variants.length === 0 || !product.in_stock || (selected !== null && !selected.in_stock);
  const stockLabel = selected
    ? selected.in_stock
      ? selected.low_stock
        ? "Only a few left"
        : "In stock"
      : "Sold out in this option"
    : product.in_stock
      ? null
      : "Currently sold out";

  return (
    <div className={styles.layout}>
      <ProductGallery images={product.images} name={product.name} slug={product.slug} focusVariantIds={focusVariantIds} />

      <div className={styles.panel}>
        <div className={styles.titleBlock}>
          {eyebrow}
          <h1 className={styles.title}>{product.name}</h1>
          <Price
            price={selected ? selected.price : product.price}
            fromPrice={selected ? undefined : lowest}
            priceVaries={!selected && priceVaries}
            size="lg"
          />
          {product.short_description && <p className={styles.lede}>{product.short_description}</p>}
        </div>

        {hasColours && (
          <fieldset className={styles.option}>
            <legend className={styles.optionLegend}>
              Colour: <span className={styles.optionValue}>{colour ?? "Choose"}</span>
            </legend>
            <div className={styles.swatches}>
              {product.colours.map((c) => (
                <ColourSwatch
                  key={c}
                  colourName={c}
                  name={colourGroup}
                  hex={colourHex(c)}
                  type="radio"
                  aria-label={`${c}${colourInStock(c) ? "" : " (sold out)"}`}
                  unavailable={!colourInStock(c)}
                  checked={colour === c}
                  onChange={() => {
                    setColour(c);
                    setShowSizeError(false);
                  }}
                />
              ))}
            </div>
          </fieldset>
        )}

        {hasSizes && (
          <fieldset className={styles.option} aria-describedby={showSizeError ? errorId : undefined}>
            <div className={styles.optionHead}>
              <legend className={styles.optionLegend}>
                Size: <span className={styles.optionValue}>{size ?? "Choose a size"}</span>
              </legend>
              {chartUsable && (
                <button type="button" className={styles.sizeGuide} onClick={() => setSizeChartOpen(true)}>
                  <Ruler aria-hidden="true" size={16} /> Size guide
                </button>
              )}
            </div>
            <div className={styles.sizes}>
              {product.sizes.map((s) => {
                const available = sizeInStock(s);
                return (
                  <ChoiceChip
                    key={s}
                    type="radio"
                    name={sizeGroup}
                    label={s}
                    unavailable={!available}
                    aria-label={`${s}${available ? "" : " (sold out)"}`}
                    checked={size === s}
                    onChange={() => {
                      setSize(s);
                      setShowSizeError(false);
                    }}
                  />
                );
              })}
            </div>
            {showSizeError && (
              <p id={errorId} className={styles.error} role="alert">
                Please choose a {hasColours && !colour ? "colour and size" : "size"}.
              </p>
            )}
          </fieldset>
        )}

        <div className={styles.stockRow}>
          {stockLabel && (
            <Badge tone={selected?.in_stock || (!selected && product.in_stock) ? "gold" : "muted"}>{stockLabel}</Badge>
          )}
          <p className={styles.sku}>
            SKU <span>{selected?.sku ?? product.sku}</span>
          </p>
        </div>

        <div className={styles.quantityRow}>
          <span className={styles.optionLegend} aria-hidden="true">
            Quantity
          </span>
          <QuantityStepper value={quantity} onChange={setQuantity} label="Quantity" disabled={soldOut} />
        </div>

        <div className={styles.actions}>
          <Button
            size="lg"
            fullWidth
            onClick={() => void addToBag()}
            loading={busy === "bag"}
            disabled={soldOut || busy !== null}
            iconStart={<ShoppingBag aria-hidden="true" />}
            aria-describedby={showSizeError ? errorId : undefined}
          >
            {soldOut ? "Sold out" : "Add to bag"}
          </Button>
          <WishlistButton slug={product.slug} name={product.name} variant="inline" />
        </div>
        {!soldOut && (
          <div className={styles.secondaryActions}>
            <Button
              variant="outline"
              size="lg"
              fullWidth
              onClick={() => void addToBag("checkout")}
              loading={busy === "buy"}
              disabled={busy !== null}
              iconStart={<Zap aria-hidden="true" />}
            >
              Buy now
            </Button>
            {whatsappEnabled && (
              <Button
                variant="soft"
                size="lg"
                fullWidth
                onClick={() => void orderOnWhatsApp()}
                loading={whatsapp.opening}
                disabled={busy !== null}
                iconStart={<MessageCircle aria-hidden="true" />}
              >
                Order on WhatsApp
              </Button>
            )}
          </div>
        )}

        {notes.length > 0 && (
          <ul className={styles.notes}>
            {notes.map((note) => (
              <li key={note.text}>
                <span className={styles.noteIcon}>
                  <Icon name={note.icon} size={18} />
                </span>
                {note.text}
              </li>
            ))}
          </ul>
        )}

        <div className={styles.details}>{details}</div>
      </div>

      {whatsapp.dialog}

      {chartUsable && chart && (
        <Dialog open={sizeChartOpen} onClose={() => setSizeChartOpen(false)} title={chart.name ?? "Size guide"}>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className="visually-hidden">Size guide{chart.unit ? ` (measurements in ${chart.unit})` : ""}</caption>
              <thead>
                <tr>
                  {chart.columns?.map((column) => (
                    <th key={column} scope="col">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chart.rows?.map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, cellIndex) =>
                      cellIndex === 0 ? (
                        <th key={cellIndex} scope="row">
                          {cell}
                        </th>
                      ) : (
                        <td key={cellIndex}>{cell}</td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {chart.unit && <p className={styles.chartUnit}>Measurements in {chart.unit}.</p>}
        </Dialog>
      )}
    </div>
  );
}

function variantLabel(variant: ProductVariant): string {
  return [variant.size, variant.colour].filter(Boolean).join(" / ");
}
