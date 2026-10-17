import { Suspense } from "react";

import type { HomepageSection, SiteContent } from "@/lib/content/types";
import { Assurances } from "./Assurances";
import { CategoryShowcase, CategoryShowcaseSkeleton } from "./CategoryShowcase";
import { ContactCta } from "./ContactCta";
import { AnnouncementStrip, FaqBlock, OccasionSpotlight, RichTextBlock } from "./ContentSections";
import { FeaturedCollections } from "./FeaturedCollections";
import { Hero } from "./Hero";
import { ProductShowcase, ProductShowcaseSkeleton } from "./ProductShowcase";
import { PromoBanner } from "./PromoBanner";
import { Testimonials } from "./Testimonials";

/**
 * Renders published homepage sections in CMS-defined order. Sections whose data is already
 * resolved by the CMS render immediately; rule-based (fixture) sections stream behind skeletons.
 */
export function HomeSections({ sections, content }: { sections: HomepageSection[]; content: SiteContent }) {
  return sections.map((section) => {
    switch (section.type) {
      case "hero":
        return <Hero key={section.id} section={section} />;
      case "category_showcase":
        return (
          <Suspense key={section.id} fallback={<CategoryShowcaseSkeleton />}>
            <CategoryShowcase section={section} />
          </Suspense>
        );
      case "product_rail":
        return (
          <Suspense key={section.id} fallback={<ProductShowcaseSkeleton />}>
            <ProductShowcase section={section} />
          </Suspense>
        );
      case "featured_collections":
        return <FeaturedCollections key={section.id} section={section} />;
      case "promo_banner":
        return <PromoBanner key={section.id} section={section} />;
      case "occasion":
        return <OccasionSpotlight key={section.id} section={section} />;
      case "assurances":
        return <Assurances key={section.id} section={section} />;
      case "testimonials":
        return <Testimonials key={section.id} section={section} />;
      case "faq":
        return <FaqBlock key={section.id} section={section} />;
      case "announcement_strip":
        return <AnnouncementStrip key={section.id} section={section} />;
      case "rich_text":
        return <RichTextBlock key={section.id} section={section} />;
      case "contact":
        return <ContactCta key={section.id} section={section} contact={content.contact} />;
      default:
        return null; // Unknown section types are skipped safely.
    }
  });
}
