import { Skeleton, SkeletonGroup } from "../../shared/ui/Skeleton";

export function PublicationSkeleton({ variant = "post" }: { variant?: "post" | "article" }) {
  if (variant === "article") return <div className="article-preview-skeleton">
    <Skeleton style={{ width: "76%", height: 27 }} />
    <Skeleton /><Skeleton style={{ width: "90%" }} />
    <Skeleton style={{ width: 120, height: 18 }} />
  </div>;

  return <div className="feed-post publication-skeleton">
    <div className="post-layout">
      <Skeleton variant="circle" className="publication-skeleton-avatar" />
      <div className="publication-skeleton-copy">
        <Skeleton style={{ width: "56%", height: 14 }} />
        <Skeleton /><Skeleton style={{ width: "92%" }} /><Skeleton style={{ width: "64%" }} />
        <div className="publication-skeleton-actions">
          <Skeleton style={{ width: 34 }} /><Skeleton style={{ width: 34 }} /><Skeleton style={{ width: 34 }} />
        </div>
      </div>
    </div>
  </div>;
}

export function PublicationListSkeleton({ count = 3, variant = "post", label = "Loading publications…" }: {
  count?: number;
  variant?: "post" | "article";
  label?: string;
}) {
  return <SkeletonGroup label={label} className={`publication-list-skeleton publication-list-skeleton-${variant}`}>
    {Array.from({ length: count }, (_, index) => <PublicationSkeleton key={index} variant={variant} />)}
  </SkeletonGroup>;
}

export function PublicationPageSkeleton({ kind }: { kind?: "article" | "micro_post" }) {
  return <div className={kind === "article" ? "reader" : "post-detail"} aria-busy="true">
    <SkeletonGroup label={kind === "article" ? "Loading article…" : kind === "micro_post" ? "Loading post…" : "Loading publication…"}>
      {kind === "micro_post" ? <PublicationSkeleton /> : <div className="reader-skeleton">
        <Skeleton style={{ width: "28%", height: 11 }} />
        <Skeleton className="reader-skeleton-title" style={{ width: "90%" }} />
        <Skeleton className="reader-skeleton-title" style={{ width: "64%" }} />
        <div className="reader-skeleton-paragraph">
          <Skeleton /><Skeleton /><Skeleton style={{ width: "86%" }} />
        </div>
        {kind === "article" && <div className="reader-skeleton-paragraph">
          <Skeleton /><Skeleton /><Skeleton style={{ width: "72%" }} />
        </div>}
      </div>}
    </SkeletonGroup>
  </div>;
}
