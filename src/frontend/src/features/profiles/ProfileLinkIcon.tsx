import type { ProfileLink } from "../../shared/api/types";
import { platformIconPaths } from "../../assets/platforms/paths";
import { Icon } from "../../shared/ui/Icon";

export function ProfileLinkIcon({ platform }: { platform: ProfileLink["platform"] }) {
  const path = Object.hasOwn(platformIconPaths, platform) ? platformIconPaths[platform] : undefined;

  if (!path) return <Icon name="link" className="profile-link-icon" width={16} height={16} focusable="false" />;

  return <svg className="profile-link-icon" width="16" height="16" viewBox="0 0 24 24"
    fill="currentColor" aria-hidden="true" focusable="false">
    <path d={path} />
  </svg>;
}
