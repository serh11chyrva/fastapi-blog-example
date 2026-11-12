import type { CSSProperties, ReactNode } from "react";

export function Skeleton({ variant = "line", className = "", style }: {
  variant?: "line" | "circle" | "block";
  className?: string;
  style?: CSSProperties;
}) {
  return <span aria-hidden="true" className={`skeleton skeleton-${variant} ${className}`} style={style} />;
}

export function SkeletonGroup({ label, children, className = "" }: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return <>
    <span className="sr-only" role="status">{label}</span>
    <div className={`loading-skeleton ${className}`} aria-busy="true">
      <div className="skeleton-shapes" aria-hidden="true">{children}</div>
    </div>
  </>;
}
