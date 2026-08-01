import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[2px] text-sm font-medium transition-colors duration-150 ease-out disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--color-bg-ink)] text-[var(--color-text-on-ink)] border border-[var(--color-bg-ink)] hover:bg-[var(--color-accent-hover)] hover:border-[var(--color-accent-hover)]",
        secondary:
          "bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-overlay)]",
        ghost:
          "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
        outline:
          "border border-[var(--color-border-strong)] text-[var(--color-text-primary)] bg-transparent hover:border-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
        ink: "bg-[var(--color-bg-ink)] text-[var(--color-text-on-ink)] border border-[var(--color-bg-ink)] hover:bg-[var(--color-accent-hover)] hover:border-[var(--color-accent-hover)]",
        accent:
          "bg-[var(--color-accent)] text-[var(--color-accent-ink)] border border-[var(--color-accent-deep)] hover:bg-[var(--color-accent-hover)]",
        danger:
          "bg-[var(--color-error)] text-[var(--color-bg-base)] hover:brightness-110",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-9 px-4",
        lg: "h-11 px-6 text-[15px]",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
