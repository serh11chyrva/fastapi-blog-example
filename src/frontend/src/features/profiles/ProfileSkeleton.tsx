import { Skeleton, SkeletonGroup } from "../../shared/ui/Skeleton";
import { PublicationSkeleton } from "../publications/PublicationSkeleton";

export function ProfileSkeleton() {
  return <div aria-busy="true">
    <SkeletonGroup label="Loading profile…">
      <div className="profile-section">
        <div className="profile-cover"><Skeleton variant="block" style={{ height: "100%", borderRadius: 0 }} /></div>
        <div className="profile-details">
          <div className="profile-controls">
            <div className="profile-portrait"><Skeleton variant="circle" style={{ width: "100%", height: "100%" }} /></div>
            <div className="profile-actions"><Skeleton variant="block" style={{ width: 100, height: 40 }} /></div>
          </div>
          <div className="profile-skeleton-copy">
            <Skeleton style={{ width: "52%", height: 24 }} /><Skeleton style={{ width: "30%" }} />
            <Skeleton style={{ width: "88%" }} /><Skeleton style={{ width: "74%" }} />
            <Skeleton style={{ width: "46%" }} /><Skeleton style={{ width: "58%" }} />
          </div>
        </div>
      </div>
      <div className="profile-skeleton-tabs"><Skeleton /><Skeleton /></div>
      {Array.from({ length: 3 }, (_, index) => <PublicationSkeleton key={index} />)}
    </SkeletonGroup>
  </div>;
}
