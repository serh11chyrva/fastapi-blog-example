import type { Attachment } from "../../shared/api/types";

type Embed = Extract<Attachment, { type: "embed" }>;

export function embedSource(item: Embed): string | null {
  try {
    const url = new URL(item.url);
    if (url.protocol !== "https:" || url.username || url.password || url.port) return null;
    const path = url.pathname.split("/").filter(Boolean);
    const host = url.hostname;
    if (item.provider === "youtube") {
      const youtube = ["www.youtube.com", "youtube.com", "www.youtube-nocookie.com"].includes(host);
      const id = host === "youtu.be" && path.length === 1 ? path[0]
        : youtube && path.length === 1 && path[0] === "watch" ? url.searchParams.get("v")
        : youtube && path.length === 2 && ["embed", "shorts", "live"].includes(path[0]) ? path[1] : null;
      if (id && /^[\w-]{11}$/.test(id)) return `https://www.youtube-nocookie.com/embed/${id}`;
    }
    if (item.provider === "vimeo") {
      const id = ["vimeo.com", "www.vimeo.com"].includes(host) && path.length === 1 ? path[0]
        : host === "player.vimeo.com" && path.length === 2 && path[0] === "video" ? path[1] : null;
      if (id && /^\d{1,20}$/.test(id)) {
        const hash = url.searchParams.get("h");
        return `https://player.vimeo.com/video/${id}${hash && /^[\da-f]{1,32}$/i.test(hash) ? `?h=${hash}` : ""}`;
      }
    }
    if (item.provider === "spotify" && host === "open.spotify.com") {
      const [kind, id, ...extra] = path[0] === "embed" ? path.slice(1) : path;
      if (["track", "album", "playlist", "episode", "show"].includes(kind) && id && /^[a-z\d]{1,64}$/i.test(id) && !extra.length)
        return `https://open.spotify.com/embed/${kind}/${id}`;
    }
    if (item.provider === "soundcloud") {
      const resource = host === "w.soundcloud.com" && path.join("/") === "player"
        ? new URL(url.searchParams.get("url") ?? "") : url;
      if (resource.protocol !== "https:" || resource.port || resource.username || resource.password) return null;
      const track = ["soundcloud.com", "www.soundcloud.com"].includes(resource.hostname)
        && /^\/[\w-]+\/(?:sets\/)?[\w-]+\/?$/.test(resource.pathname);
      const apiTrack = host === "w.soundcloud.com" && resource.hostname === "api.soundcloud.com" && /^\/(?:tracks|playlists)\/\d+\/?$/.test(resource.pathname);
      if (track || apiTrack) {
        resource.search = "";
        resource.hash = "";
        return `https://w.soundcloud.com/player/?url=${encodeURIComponent(resource.toString())}`;
      }
    }
  } catch {
    return null;
  }
  return null;
}
