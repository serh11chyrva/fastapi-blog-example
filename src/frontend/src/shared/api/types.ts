import type { JSONContent } from "@tiptap/core";
export type ProfileCard = {
  id: string;
  username: string;
  display_name: string;
  avatars: { original: string | null };
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
export type PublicationKind = "micro_post" | "article";
export type Attachment =
  | { type: "image"; url: string; alt: string }
  | { type: "link"; url: string; label: string | null }
  | { type: "mention"; user_id: string }
  | { type: "hashtag"; tag: string }
  | { type: "og_card"; url: string; title: string; description: string; image_url: string | null; site_name: string | null }
  | { type: "article"; article_id: string }
  | { type: "embed"; provider: "soundcloud" | "spotify" | "youtube" | "twitch"; url: string }
  | { type: "video"; url: string };
export type PublicationBase = {
  id: string;
  share_url: string | null;
  owner_id: string;
  authors: ProfileCard[];
  attachments: Attachment[];
};
export type PostFeedItem = PublicationBase & {
  kind: "micro_post";
  text: string;
  published_at: string;
};
export type ArticleFeedItem = PublicationBase & {
  kind: "article";
  title: string;
  summary: string;
  thumbnail_url: string | null;
  published_at: string;
};
export type OriginalFeedItem = PostFeedItem | ArticleFeedItem;
export type RepostFeedItem = {
  id: string;
  kind: "repost";
  reposted_by: ProfileCard;
  published_at: string;
  post: PostFeedItem;
};
export type FeedItem = OriginalFeedItem | RepostFeedItem;
export type CursorPage<T> = { items: T[]; next_cursor: string | null };
export type Feed = CursorPage<FeedItem>;
export type MicroPost = PublicationBase & {
  kind: "micro_post";
  text: string;
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
export type InteractionAction = "like" | "save" | "repost";
export type InteractionSummary = {
  likes_count: number;
  comments_count: number;
  reposts_count: number | null;
  liked: boolean;
  saved: boolean;
  reposted: boolean | null;
};
export type SavedPublication = { id: string; saved_at: string; publication: OriginalFeedItem };
type CommentContent = {
  id: string;
  author: ProfileCard | null;
  text: string | null;
  created_at: string;
  updated_at: string;
  deleted: boolean;
};
export type PostReply = CommentContent & {
  post_id: string;
  parent_id: string | null;
  root_id: string;
  depth: number;
  replies_count: number;
};
export type ArticleComment = CommentContent & { article_id: string };
export type DiscussionComment = PostReply | ArticleComment;
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
  likes_count: number;
  liked: boolean;
