import type { JSONContent } from "@tiptap/core";
export type ProfileCard = {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
};
export type User = Pick<ProfileCard, "id" | "username" | "display_name"> & {
  email: string;
};
export type ProfileLinkInput = {
  version?: 1;
  id?: string;
  label: string;
  url: string;
};
export type ProfileLink = ProfileLinkInput & {
  version: 1;
  id: string;
  platform: string;
  redirect_url: string;
};
export type ProfileBadge = {
  version: 2;
  code: string;
  payload: {
    label: string;
    description: string | null;
    background_color: string;
    text_color: string;
    icon_url: string | null;
    icon_color: string | null;
  };
};
export type OwnerBadge = ProfileBadge & {
  assigned_at: string;
  preferences: {
    enabled: boolean;
  };
  permissions: {
    can_disable: boolean;
  };
};
export type Profile = ProfileCard & {
  bio: string;
  links: ProfileLink[];
  badges: ProfileBadge[];
  follower_count: number;
  following_count: number;
  is_following: boolean;
};
export type OwnProfile = Omit<Profile, "badges"> & {
  revision: number;
  badges: OwnerBadge[];
};
type Author = {
  author_id: string;
  author_username: string;
  author_display_name: string;
  author_avatar_url: string | null;
};
type PublicationBase = Author & {
  id: string;
  share_url: string | null;
};
export type FeedItem = PublicationBase & {
  published_at: string;
} & ({
  kind: "micro_post";
  text: string;
  images: string[];
  title: null;
  summary: null;
  thumbnail_url: null;
} | {
  kind: "article";
  title: string;
  summary: string;
  thumbnail_url: string | null;
  text: null;
  images: [
  ];
});
export type Feed = {
  items: FeedItem[];
  next_cursor: string | null;
};
export type MicroPost = PublicationBase & {
  kind: "micro_post";
  text: string;
  images: string[];
  created_at: string;
  updated_at: string;
};
export type Article = PublicationBase & {
  kind: "article";
  title: string;
  summary: string;
  body: JSONContent;
  thumbnail_url: string | null;
  inline_image_urls: string[];
  status: "draft" | "scheduled" | "published";
  created_at: string;
  updated_at: string;
  scheduled_at: string | null;
  published_at: string | null;
};
export type Session = {
  id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  client_type: "web" | "mobile" | "desktop";
  location: string;
  device: string;
  current: boolean;
};
