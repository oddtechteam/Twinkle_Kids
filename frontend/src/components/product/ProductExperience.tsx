"use client";

import { Ruler, ShoppingBag } from "lucide-react";
import { type ReactNode, useId, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { ChoiceChip, ColourSwatch } from "@/components/ui/Form";
import { Icon } from "@/components/ui/Icon";
import { Price } from "@/components/ui/Price";
import { useToast } from "@/components/ui/Toast";
import type { ProductDetail, ProductVariant } from "@/lib/api/types";
import { useBag } from "@/lib/bag/BagProvider";
import type { IconName } from "@/lib/content/types";
import { ProductGallery } from "./ProductGallery";
import { WishlistButton } from "./WishlistButton";
import styles from "./ProductExperience.module.css";

interface Props {
  product: ProductDetail;
  notes: { icon: IconName; text: string }[];
  eyebrow?: ReactNode;
  /** Server-rendered description and details. */
  details: ReactNode;
}

/** Gallery + purchase panel sharing the selected colour/size. Prices come from the variant's PriceView. */
export function ProductExperience({ product, notes, eyebrow, details }: Props) {
  const variants = product.variants.filter((v) => v.is_active);
  const hasColours = product.colours.length > 0;
  const hasSizes = product.sizes.length > 0;

  const firstAvailableColour =
    product.colours.find((c) => variants.some((v) => v.colour === c && v.in_stock)) ?? product.colours[0] ?? null;
  const [colour, setColour] = useState<string | null>(hasColours ? firstAvailableColour : null);
  const [size, setSize] = useState<string | null>(product.sizes.length === 1 ? (product.sizes[0] ?? null) : null);
  const [showSizeError, setShowSizeError] = useState(false);
  const [sizeChartOpen, setSizeChartOpen] = useState(false);
  const [adding, setAdding] = useState(false);

  const bag = useBag();
  const toast = useToast();
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

  async function addToBag() {
    if (!selected) {
      setShowSizeError(true);
      return;
    }
    setAdding(true);
    const result = await bag.add(selected.id, 1);
    setAdding(false);
    if (result.ok) {
      toast.show({ title: "Added to your bag", description: product.name });
    } else if (result.reason === "unavailable") {
      toast.show({
        tone: "info",
        title: "Online bag opens soon",
        description: "Save this style to your wishlist and we'll be ready for you shortly.",
      });
    } else {
      toast.show({ tone: "warning", title: "Couldn't add to bag", description: "Please try again." });
    }
  }

  const stockLabel = selected
    ? selected.in_stock
      ? "In stock"
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
            <Badge tone={stockLabel === "In stock" ? "gold" : "muted"}>{stockLabel}</Badge>
          )}
        </div>

        <div className={styles.actions}>
          <Button
            size="lg"
            fullWidth
            onClick={addToBag}
            loading={adding}
            disabled={selected !== null && !selected.in_stock}
            iconStart={<ShoppingBag aria-hidden="true" />}
            aria-describedby={showSizeError ? errorId : undefined}
          >
            {selected && !selected.in_stock ? "Sold out" : "Add to bag"}
          </Button>
          <WishlistButton slug={product.slug} name={product.name} variant="inline" />
        </div>

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
