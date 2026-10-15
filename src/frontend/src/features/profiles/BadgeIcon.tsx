import type { ProfileBadge } from "../../shared/api/types";
export function BadgeIcon({ badge }: {
  badge: ProfileBadge;
}) {
  const { icon_url, icon_color } = badge.payload;
  if (!icon_url)
    return null;
  return icon_color ? <span className="inline-block h-3.5 w-3.5 shrink-0" aria-hidden="true" style={{ backgroundColor: icon_color, maskImage: `url(${icon_url})`, WebkitMaskImage: `url(${icon_url})`, maskSize: "contain", maskRepeat: "no-repeat", maskPosition: "center" }} /> : <img src={icon_url} className="h-3.5 w-3.5" alt="" aria-hidden="true" />;
}
