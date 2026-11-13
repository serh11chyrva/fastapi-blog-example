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
