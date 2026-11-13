# Demo data and feature tour

Provision Garage using the startup guide, then build, start, and seed the stack.

```sh
docker compose up --build -d --wait
docker compose exec -T api python -m backend.seed
```

The seed requires the configured MongoDB database, Redis, and both private image buckets.
See the [startup guide](../README.md#start-the-application) for initial setup.
It never drops collections, clears buckets, resets existing passwords, or overwrites
existing publication fixtures. Stable IDs and image keys make repeated runs additive,
including after a partial failure. Missing demo relationships are restored. Missing
profile links, badge assignments, and avatars are filled without replacing existing values.
Locations and banners are added once to selected profiles so later edits and removals are
preserved. Previously revoked or expired example sessions are not reactivated. User-edited,
deleted, or unpublished fixture publications retain their current state.

The earlier three-post/two-article sample is preserved if it already exists. A fresh run
adds 7 demo accounts, 37 posts, 13 articles, 12 follow relationships, 9 example sessions,
36 post replies, and 32 article comments. Alice has more than 20 saves and reposts.
Existing application data can make database totals higher. Scheduled dates are relative
to first creation and are not moved forward on every seed run.

All fixture text is English. PNG landscape illustrations and avatars are generated
locally with the Python standard library and uploaded to the configured Garage buckets.
Alice and Dana also have wide landscape banners.
There are no external image downloads or new Python dependencies. Fixture writes and
their demo audit records commit together; normal browser mutations still use application
services and their own audit events.

## Search tour

After seeding, complete the [search backfill and Atlas index setup](SEARCH.md#initial-setup-and-maintenance).
Open Search as a guest or signed-in user. Search `alice` to find a profile, or
`workbench` to find article text, posts, and discussion entries. Compare Relevance
and Latest; search a passage beyond an article's first 280 characters to exercise
full-body matching. Click the structured `#SmallSteps` tag in a showcase article
to open exact-tag search. New Unicode hashtags in names, bios, posts, or article
text become clickable without rewriting saved article JSON. Queries with more
than three matching people expose Show more above the mixed publication list.
Indexing can lag briefly behind newly seeded or edited data.

## Sign in

New demo password identities use the value of `DEMO_PASSWORD` in `.env`.
Existing identities keep their current password.

| Email / username | Useful examples |
| --- | --- |
| `alice@example.com` / `alice` | Publishing workbench article, banner, Saved pagination, a mixed profile timeline, hidden and mandatory badges |
| `ben@example.com` / `ben` | Five-image gallery, private draft, scheduled article, saved items |
| `casey@example.com` / `casey` | Article comments with links to the discussion, reposts, and session settings |
| `dana@example.com` / `dana` | Design articles, featured-author credits, and follows |
| `elena@example.com` / `elena` | Photography notes and featured-author credits |
| `farah@example.com` / `farah` | Software articles, comments, and author credits |
| `noah@example.com` / `noah` | Empty profile, no avatar, empty publication/network/saved lists |

Open the application at the configured origin, normally
[http://localhost:8080](http://localhost:8080). The seed prints direct URLs for the
rich note, five-image gallery, publishing workbench, and a direct link to a ranked comment.

## Publications and editor

- Explore has enough original posts and reposts for several cursor pages. Filter between
  short notes and articles, then compare it with Following after signing in.
- **Field note 01**, owned by Alice, combines an image, mention, hashtag, plain link,
  caller-supplied Open Graph card, and a published article reference.
- **Field note 02**, owned by Ben, has five uploaded images with alternate text and a
  featured author. New demo posts also include an article card and a quoted micro-post with
  replies available through its publication-page discussion.
- **A reading room for small ideas**, owned by Alice, includes a cover, two inline images,
  three heading levels, bold/italic/strike/inline-code marks, an external link, a hard break,
  bullet and ordered lists, a blockquote, code block, horizontal rule, inline mention and
  hashtag, and attachment blocks. It also credits Dana and Farah.
- **Notes from the publishing workbench** demonstrates aligned text, underline, a quote citation,
  a code language, an updated date, a link card, and click-to-load SoundCloud, Spotify, YouTube,
  and Vimeo players. Existing demo installs receive this article as a separate publication.
- Sign in as Alice or Ben and open **My articles** to filter published, draft, and scheduled
  content. The private notebook/workbench examples are drafts. Two scheduled stories are
  initially due one and seven days after first seeding; the application scheduler publishes
  them when due. Use the editor to choose a nearer future time when exploring scheduling.
- Draft and scheduled articles and their images are owner-only. Featured authors receive
  display credits without editing or private-read access. Compare an owner session with an
  anonymous browser window.
- Edit a note, create a new note with images, save an article draft, upload a cover or inline
  image, publish it, copy its share link, and return it to draft. Existing rich nodes survive
  editor round trips. Selecting a local image checks its type and size before creating a post.

## Profiles and account controls

Public profiles demonstrate avatars, banners, locations, join dates, post and follower counts,
links with stable redirects, badge styles, and featured-author credits. Supported link platforms
show their logos in black and white, with a black accent, both in the profile header and the
**All links** dialog. Ordinary websites and unknown platform identifiers use the generic link icon.
The Posts tab mixes authored posts, reposts, and comments with an attached article card.
The Articles tab lists authored articles.
Visit Casey's profile for the publishing workbench comment and follow its link into the article.

Open **Settings → Profile** to crop an avatar or banner before uploading it. Drag a
profile link's handle or focus it and use the arrow keys to move the link. Select
**Save profile** to publish the new order.

Alice's profile settings include a visible optional badge, a required Community Guide
badge, and a hidden Workshop Member badge. Toggle optional visibility or edit a link.
Open settings in two tabs to explore revision conflicts without overwriting newer changes.

Open **Settings → Active sessions** to review session details. Alice, Ben, and Casey
have illustrative web, mobile, and desktop sessions alongside the browser session
created on login. Native examples are labeled Demo phone and
Demo laptop. Their tokens are discarded by the seed and are never printed. Location is
unknown when no real IP metadata is available. Revoke an example or use Log out other
sessions; the current real browser session remains active.

## Reactions and discussion

Like and save posts/articles, repost posts, and compare pressed states between an original
and its repost. Article reposts are deliberately unsupported. Alice's Saved page and profile timeline
both span multiple pages. Private saves are visible only to their owner.

The rich note has 26 root entries, a six-level reply chain, and a deleted parent with two
live children. Expand Show replies one level at a time. The reading-room article has 26 root
comments, and the publishing workbench has six. Compare Most liked and Newest first on the
workbench. The two ranked replies under the quote and the seeded comment likes demonstrate that
order. Seeding restores missing demo likes without duplicating existing reactions.

Alice and the other participants own different comments, so switching accounts demonstrates
edit/delete permissions. Publication ownership does not grant moderation over other authors.

## API reference and boundaries

Open [the API reference](http://localhost:8080/api/docs) for exact routes, payloads, and
examples. Anonymous visitors can read public profiles, publications, and discussions.
Authentication, Origin checks, revision conflicts, upload validation, and private visibility
remain enforced by the ordinary API.

The demo link cards ship with text metadata. To try automatic preview, paste an external
URL into the composer or editor. Provider playback depends on the provider and loads only
after the reader activates a player.

Discussion fixtures are converted into reply posts using the same resumable migration
as existing data. Repeated seeding preserves already migrated owner edits and deletions.
Replies share the 280-character post limit and can be saved or reposted.

New post fixtures use one attachment choice each. `note-01` is an image-only
five-image gallery, `note-07` is a card-only post, `note-08` contains a plain link,
and `note-09` references a published article when available. Existing fixtures are
not overwritten; normalize their old mixed attachments through the explicit
migration before starting this version.
