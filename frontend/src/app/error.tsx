"use client";

import { RotateCcw } from "lucide-react";

import { Button, ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container-narrow" style={{ paddingBlock: "var(--space-11)" }}>
      <EmptyState
        tone="error"
        title="Something went wrong"
        description="Sorry — this page didn't load properly. Please try again."
        action={
          <>
            <Button onClick={reset} iconStart={<RotateCcw aria-hidden="true" />}>
              Try again
            </Button>
            <ButtonLink href="/" variant="outline">
              Back to home
            </ButtonLink>
          </>
        }
      />
    </div>
  );
}
