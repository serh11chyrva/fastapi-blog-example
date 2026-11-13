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
