import {
  Gift,
  Heart,
  MessageCircle,
  Ruler,
  Shirt,
  ShieldCheck,
  Sparkles,
  Star,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";

import type { IconName } from "@/lib/content/types";

const ICONS: Record<IconName, LucideIcon> = {
  sparkles: Sparkles,
  ruler: Ruler,
  "message-circle": MessageCircle,
  gift: Gift,
  heart: Heart,
  "shield-check": ShieldCheck,
  shirt: Shirt,
  star: Star,
};

/** Renders a CMS-configurable icon by name (decorative by default). */
export function Icon({ name, ...props }: { name: IconName } & LucideProps) {
  const Component = ICONS[name] ?? Sparkles;
  return <Component aria-hidden="true" strokeWidth={1.75} {...props} />;
}
