import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "accent" | "outline" | "soft" | "ghost" | "link";
export type ButtonSize = "sm" | "md" | "lg";

interface StyleProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
}

export function buttonClass({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className,
}: StyleProps & { className?: string }): string {
  return [styles.button, styles[variant], styles[size], fullWidth && styles.full, className]
    .filter(Boolean)
    .join(" ");
}

function Content({ iconStart, iconEnd, children }: StyleProps & { children: ReactNode }) {
  return (
    <>
      {iconStart && <span className={styles.icon}>{iconStart}</span>}
      <span className={styles.label}>{children}</span>
      {iconEnd && <span className={styles.icon}>{iconEnd}</span>}
    </>
  );
}

type ButtonProps = StyleProps & ComponentProps<"button"> & { loading?: boolean };

export function Button({
  variant,
  size,
  fullWidth,
  iconStart,
  iconEnd,
  loading = false,
  className,
  children,
  type = "button",
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClass({ variant, size, fullWidth, className })}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      <Content iconStart={loading ? <span className={styles.spinner} /> : iconStart} iconEnd={iconEnd}>
        {children}
      </Content>
    </button>
  );
}

type ButtonLinkProps = StyleProps & ComponentProps<typeof Link>;

export function ButtonLink({
  variant,
  size,
  fullWidth,
  iconStart,
  iconEnd,
  className,
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <Link className={buttonClass({ variant, size, fullWidth, className })} {...rest}>
      <Content iconStart={iconStart} iconEnd={iconEnd}>
        {children}
      </Content>
    </Link>
  );
}
