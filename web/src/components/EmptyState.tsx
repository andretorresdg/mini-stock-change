import type { ReactNode } from "react";

interface EmptyStateProps {
  children: ReactNode;
}

export default function EmptyState({ children }: EmptyStateProps) {
  return (
    <p className="empty-state" role="status">
      {children}
    </p>
  );
}
