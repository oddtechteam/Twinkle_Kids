import type { Metadata, Viewport } from "next";
import { Nunito, Nunito_Sans } from "next/font/google";

import { AppProviders } from "@/components/providers/AppProviders";
import { getSiteContent } from "@/lib/content";
import { themeCss } from "@/lib/content/theme";
import "./globals.css";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["600", "700", "800", "900"],
  display: "swap",
});

const nunitoSans = Nunito_Sans({
  variable: "--font-nunito-sans",
  subsets: ["latin"],
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const { brand, seo } = await getSiteContent();
  const suffix = seo.titleSuffix || brand.name;
  return {
    title: { default: `${brand.name} — ${brand.tagline}`, template: `%s | ${suffix}` },
    description: seo.description || brand.description,
    applicationName: brand.name,
    icons: brand.faviconUrl ? { icon: brand.faviconUrl } : undefined,
    openGraph: seo.ogImageUrl ? { images: [{ url: seo.ogImageUrl }] } : undefined,
  };
}

export const viewport: Viewport = {
  themeColor: "#fff7f1", // = --tk-ivory (meta tags need a literal colour)
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const content = await getSiteContent();
  const theme = themeCss(content.theme);
  return (
    <html lang="en-IN" className={`${nunito.variable} ${nunitoSans.variable}`}>
      <head>
        {/* CMS brand colours: hex values are re-validated before being written here. */}
        {theme && <style>{theme}</style>}
      </head>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
