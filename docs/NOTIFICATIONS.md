# Notifications

The private inbox uses Beanie `NotificationEvent` source records and
`NotificationGroup` recipient-owned rows. Both collections are initialized with
the application models; existing accounts start with an empty inbox. There is no
backfill, expiry policy, or additional infrastructure requirement.

Each source action has at most one event per recipient. Likes and reposts share
a row only when their recipient, notification type, publication kind, publication
ID, and UTC calendar date match. Comments, replies, and logins each have their own
row. Social self-notifications are suppressed.

Source services own the MongoDB transaction. Creating or undoing an action must
create or retract its notifications within that same transaction. Uniqueness and
write conflicts abort the operation with 409; transaction bodies are not replayed.

Every added event receives a monotonically increasing sequence inside its group.
The group retains a read-through boundary independently of its latest surviving
event. A newer event makes the row unread. Removing an event rebuilds the count,
latest event time, and up to three recent actor IDs without resetting the sequence
counter or read boundary. Removing the last event removes the row. Retracting the
last unread event can make an older surviving group read again.

Source and group uniqueness indexes prevent duplicate memberships and rows.
Recipient/time indexes support chronological pages; recipient/read-state indexes
support unread row counts. Source events have a group/sequence index for rebuilding
membership summaries after retractions.

## API

All paths use `/api/v1`. Every endpoint requires a session and returns
`Cache-Control: private, no-store`; mutations additionally require the configured
`Origin`. There is no public notification creation endpoint.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/me/notifications` | `{items, next_cursor}`; `cursor` and `limit` query parameters |
| GET | `/me/notifications/summary` | `{unread_count}` counting rows, including unavailable targets |
| PUT | `/me/notifications/read` | Version-bounded receipt batch; 204 |
| PUT | `/me/notifications/read-all` | Current server snapshot marked read; no body; 204 |

Pages contain 20 rows by default, accept limits from 1 to 50, and sort by
`last_event_at` and group ID descending. Pass the opaque `next_cursor` unchanged.
Invalid cursors and request bodies return 422. Group activity and retractions can
move rows between pages; clients merge by group ID and restart pagination when
refreshing. Counts and pages are independent live reads rather than one snapshot.

Example row:

```json
{
  "id": "68ebd423f2b7a8c901234564",
  "version": 3,
  "is_read": false,
  "last_event_at": "2026-11-13T10:10:00Z",
  "kind": "like",
  "event_count": 2,
  "actors": [{
    "id": "68eb7491d37a2f06b8ce9540",
    "username": "elliot_gray",
    "display_name": "Elliot Gray",
    "avatars": {"original": null}
  }],
  "target": {
    "kind": "micro_post",
    "id": "68eb856f7a02c1349de6b580",
    "available": true,
    "label": "post",
    "url": "/posts/68eb856f7a02c1349de6b580",
    "preview": "A reading note."
  }
}
```

`kind` discriminates `like`, `comment`, `reply`, `repost`, and `login`. Social rows
include a surviving action count and up to three recent, currently existing public
actor cards. Missing actors remain included in the count. Social content is never
copied into stored notifications. Previews resolve public posts and articles in
batches, applying original, ancestor, archive, draft, deletion, and discussion
visibility. An unavailable target keeps its reference but uses `available: false`,
`label: "publication"`, `preview: null`, and `url: null`. Its row can still be read
and counted, and a restored public target becomes available on a later read.
Closing an article discussion affects its replies, not notifications about likes
on the article itself. Comment/reply destinations open the reply post directly.

Example receipt body:

```json
{"items": [{"id": "68ebd423f2b7a8c901234564", "through_version": 3}]}
```

Accept one to fifty items. The boundary advances monotonically and is capped at
the group's issued sequence; duplicate IDs use the maximum submitted version.
Missing or foreign groups are ignored without revealing ownership. A new event
with a later sequence remains unread when an old displayed version is marked.
Read receipts affect inbox state only and do not append per-row audit events.

Read-all uses one MongoDB transaction to mark its snapshot's unread groups through
their issued sequences. Later inserted groups remain unread. Concurrent writes to
selected groups may return 409; clients reconcile and require an explicit retry
instead of replaying the whole operation. Database failures can have uncertain
commit outcomes, so refresh before retrying. Other recipients are never selected.

## Social event sources

`InteractionService.set_state` emits for a newly created like or post repost,
including reactions on reply posts. Only the target's owner receives the event;
featured authors and the initiator are excluded. Repeated PUT operations create
no extra event. Removing the edge retracts its notification source even when its
publication is no longer public. Re-adding creates a new source event in the
appropriate current UTC-day group. Private saves do not create notifications.

`CommentService.create` notifies the original publication owner with `comment`.
When there is an immediate parent, its owner also receives `reply`; the reply
category wins when both recipients are the same. The author is always excluded.
This uses immutable original/parent metadata, including requests through a reply's
post route. Reusing an already published upload draft returns the existing reply
without emitting again. Edits change the current preview without another event.

`PostService.delete` retracts the deleted reply's creation source for all recipients,
including deletion through compatibility comment routes. Other action events
whose target becomes unavailable remain as placeholders. Source mutation, search
updates where applicable, notifications, and the existing audit are committed in
the same transaction. Archiving, unpublishing, or closing a discussion retains
events and changes only their current target availability.

## Successful login notifications

`SessionService.create` adds one `login` notification in the transaction that
persists the new session, any password hash upgrade, and `LOGIN_SUCCEEDED` audit.
Every successful password login produces an event, rather than attempting to
infer whether a device is new. Registration, rejected credentials, and ordinary
session restoration do not emit events.

Readable device and approximate location labels use the existing session
presentation helpers and local optional GeoIP database. They are captured off the
event loop before the transaction. Missing data uses `Unknown browser`,
`Unknown device`, or `Unknown location` as appropriate. The notification does not
contain raw IP addresses, raw User-Agents, password data, or session tokens.
Later activity, expiry, and revocation do not alter or remove the captured event.

Example login row:

```json
{
  "id": "68ebd423f2b7a8c901234565",
  "version": 1,
  "is_read": false,
  "last_event_at": "2026-11-13T10:20:00Z",
  "kind": "login",
  "login": {
    "client_type": "web",
    "device": "Chrome on Windows",
    "location": "Kyiv, Ukraine"
  },
  "url": "/settings/sessions"
}
```

System categories extend the typed inbox union and internal emission service;
clients cannot supply arbitrary notification payloads through a public endpoint.

## Frontend inbox

The protected `/notifications` page appears between Profile and My articles in
the shared sidebar. Mobile More navigation includes Notifications before My
articles, with an unread indicator on More itself. The badge counts unread rows,
shows `99+` above ninety-nine, and retains the last known count during errors.
An unavailable count has an explanatory indicator and can be retried in the inbox.

One account-scoped provider polls the summary every thirty seconds and on visible
tab/window return or reconnection. Hidden tabs and offline browsers make no polling
requests. Account changes, logout, and expired sessions replace the provider,
clear local counts/receipts, and abort old requests. The provider also serves
reading layouts, so navigation never starts a second polling loop.

The inbox loads twenty rows at a time using cursor pagination and merges group
IDs without duplicates. While within 120 pixels of the top, polling refreshes
the first page and restarts continuation pagination. While reading older rows,
the list stays in place and the persistent Refresh button highlights after a
poll. Refresh explicitly returns to the top and loads a fresh first page.
Returning to the top also applies a pending refresh. Background errors retain
existing rows; initial, continuation, summary, and receipt failures expose Retry.

A row is automatically viewed after at least half of it is visible continuously
for one second in a visible, focused browser window. The observer excludes the
fixed navigation/toolbar areas; leaving the threshold, hiding the tab, or losing
focus resets the timer. Opening a target also queues a receipt for that displayed
version. Read receipts are debounced for 200 milliseconds, sent in batches of at
most fifty, and acknowledged only after successful persistence. Failed batches
remain pending until an explicit retry. Later group versions remain unread.
Browsers without IntersectionObserver retain opening and Mark all as read actions.

Mark all as read operates on the server snapshot, acknowledges only the displayed
versions locally, and refreshes the summary. It does not replay automatically on
errors. List polling and further receipt submission pause during this action;
notifications viewed during it can be submitted afterward. Newer events are never
locally marked through an older displayed version. Rows include current actor
names, a readable action, a text preview or unavailable placeholder, and relative
time with an exact timestamp tooltip. Login entries link to session settings.
