/**
 * Datasheet section header: a full-width hairline rule carrying a mono
 * index and the section title on one baseline. The one repeated grammar
 * on the landing page.
 */
export function SectionHeader({
  index,
  title,
}: {
  index: string;
  title: string;
}) {
  return (
    <div className="border-t border-[var(--color-border-default)] pt-5 mb-12 flex items-baseline gap-6">
      <span className="font-mono text-[13px] tracking-[0.1em] text-[var(--color-accent-deep)]">
        {index}
      </span>
      <h2 className="display-sub text-[clamp(1.75rem,3.2vw,2.375rem)] text-[var(--color-text-primary)]">
        {title}
      </h2>
    </div>
  );
}
