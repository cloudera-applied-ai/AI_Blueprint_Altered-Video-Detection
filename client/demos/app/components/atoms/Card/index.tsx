export default function Card({
  title,
  description,
  children,
  className = "",
}: {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-card)] ${className}`}
    >
      {title ? (
        <header className="mb-5 border-b border-[var(--border)] pb-4">
          <h2 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">{title}</h2>
          {description ? (
            <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-secondary)]">{description}</p>
          ) : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}
