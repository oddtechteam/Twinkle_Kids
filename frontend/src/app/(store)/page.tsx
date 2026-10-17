import { HomeSections } from "@/components/home/HomeSections";
import { getSiteContent, visibleSections } from "@/lib/content";

export default async function HomePage() {
  const content = await getSiteContent();
  return <HomeSections sections={visibleSections(content)} content={content} />;
}
