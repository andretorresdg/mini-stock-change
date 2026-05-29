import type { ReactNode } from "react";

interface PanelProps {
  children: ReactNode;
  title?: string;
  titleId?: string;
  "aria-label"?: string;
}

export default function Panel({ children, title, titleId, "aria-label": ariaLabel }: PanelProps) {
  const labelledBy = title && titleId ? titleId : undefined;

  return (
    <section
      className="panel"
      role="region"
      aria-labelledby={labelledBy}
      aria-label={ariaLabel}
    >
      {title && titleId && (
        <h2 id={titleId} className="panel__title">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
