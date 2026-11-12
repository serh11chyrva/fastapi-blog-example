import { Skeleton, SkeletonGroup } from "./Skeleton";

export function PeopleSkeleton({ count = 3, label = "Loading profiles…", withBio = false }: {
  count?: number;
  label?: string;
  withBio?: boolean;
}) {
  return <SkeletonGroup label={label} className="people-skeleton">
    {Array.from({ length: count }, (_, index) => <div className="person-skeleton" key={index}>
      <Skeleton variant="circle" />
      <div className="person-skeleton-copy">
        <Skeleton style={{ width: "58%" }} /><Skeleton style={{ width: "36%", height: 10 }} />
        {withBio && <Skeleton style={{ width: "86%" }} />}
      </div>
    </div>)}
  </SkeletonGroup>;
}
