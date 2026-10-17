/** CMS brand colours → CSS custom properties. Only strict #RRGGBB values are ever emitted. */

export interface ThemeColours {
  navy?: string;
  ivory?: string;
  blush?: string;
  coral?: string;
  gold?: string;
}

const HEX = /^#[0-9a-fA-F]{6}$/;
const TOKEN: Record<keyof ThemeColours, string> = {
  navy: "--tk-navy",
  ivory: "--tk-ivory",
  blush: "--tk-blush",
  coral: "--tk-coral",
  gold: "--tk-gold",
};

export function themeCss(theme: ThemeColours): string | null {
  const declarations = (Object.keys(TOKEN) as (keyof ThemeColours)[])
    .map((key) => {
      const value = theme[key];
      return value && HEX.test(value) ? `${TOKEN[key]}:${value};` : null;
    })
    .filter(Boolean);
  return declarations.length > 0 ? `:root{${declarations.join("")}}` : null;
}
