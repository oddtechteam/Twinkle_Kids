import { ButtonLink } from "@/components/ui/Button";
import { InfoPage } from "@/components/ui/InfoPage";
import { Motif } from "@/components/ui/Motif";

export default function NotFound() {
  return (
    <InfoPage
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Not found" }]}
      icon={<Motif kind="star" size={28} />}
      title="This page wandered off"
      description="We couldn't find what you were looking for. It may have moved or is no longer available."
      action={
        <>
          <ButtonLink href="/shop">Shop all styles</ButtonLink>
          <ButtonLink href="/" variant="outline">
            Back to home
          </ButtonLink>
        </>
      }
    />
  );
}
