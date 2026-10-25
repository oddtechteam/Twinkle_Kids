import { Sparkles } from "lucide-react";

import { HomeSections } from "@/components/home/HomeSections";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { getSiteContent, visibleSections } from "@/lib/content";

export default async function HomePage() {
  const content = await getSiteContent();
  const sections = visibleSections(content);

  // Nothing published (or the CMS is unreachable): say so plainly rather than inventing content.
  if (sections.length === 0) {
    return (
      <div className="section container-narrow">
        <EmptyState
          icon={<Sparkles aria-hidden="true" size={26} />}
          title={`Welcome to ${content.brand.name}`}
          description="Our homepage is being refreshed. The full collection is ready to browse in the meantime."
          action={<ButtonLink href="/shop">Shop all styles</ButtonLink>}
        />
      </div>
    );
  }

  return <HomeSections sections={sections} content={content} />;
}
