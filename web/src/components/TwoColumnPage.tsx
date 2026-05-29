import type { ReactNode } from "react";

interface TwoColumnPageProps {
  left: ReactNode;
  right: ReactNode;
}

export default function TwoColumnPage({ left, right }: TwoColumnPageProps) {
  return (
    <div className="two-column-page">
      <div className="page-column page-column--left">{left}</div>
      <div className="page-column page-column--right">{right}</div>
    </div>
  );
}
