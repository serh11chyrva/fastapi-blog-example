import { Skeleton, SkeletonGroup } from "../../shared/ui/Skeleton";

export function ReplySkeleton() {
  return <SkeletonGroup label="Loading replies…" className="reply-skeleton">
    {Array.from({ length: 2 }, (_, index) => <div className="person-skeleton" key={index}>
      <Skeleton variant="circle" />
      <div className="person-skeleton-copy">
        <Skeleton style={{ width: "48%" }} /><Skeleton /><Skeleton style={{ width: "78%" }} />
      </div>
    </div>)}
  </SkeletonGroup>;
}
