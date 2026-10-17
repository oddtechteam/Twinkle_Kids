import { AnnouncementBar } from "@/components/layout/AnnouncementBar";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { getSiteContent } from "@/lib/content";

export default async function StoreLayout({ children }: LayoutProps<"/">) {
  const content = await getSiteContent();
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <AnnouncementBar announcement={content.announcement} />
      <SiteHeader content={content} />
      <main id="main">{children}</main>
      <SiteFooter content={content} />
    </>
  );
}
