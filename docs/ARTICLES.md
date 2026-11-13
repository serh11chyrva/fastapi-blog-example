# Writing and reading articles

The article editor, article ID page, and public share page use the same heading
navigation. On screens at least 960 px wide, the right-hand indicators follow the
current section and expose heading labels on hover or keyboard focus. Long outlines
scroll within the navigation. Editor headings update immediately after edits and
reordering; section anchors are view decorations and are never saved in article JSON.

The reading page shows the complete body without repeating its generated summary
above the text or its attachment hashtags below it. Summaries remain available in
feed cards and API responses. Hashtags written inside the body remain visible.

Author cards place the public handle next to the display name and the follow action
at the right edge. Name and handle wrap on narrow screens.

## Formatting and block controls

Unaligned paragraphs use justified text, including existing articles. Explicit
alignment remains unchanged; headings default to left alignment. The selection
toolbar has alignment icons and appears only for a nonempty text selection in the
focused editor or while its formatting controls have focus. Opening publishing or
focusing the title dismisses it. Code blocks do not expose the text toolbar.

Strike is retained as a legacy JSON mark so existing articles survive editing.
The editor no longer offers strike controls, shortcuts, HTML paste conversion, or
automatic strike formatting. Block controls follow the hovered block, remain
keyboard accessible, and share the same add-button appearance. The writing surface
has no focus outline; buttons and inputs retain their focus indicators. Image
restrictions are still enforced when choosing or uploading files.

## Links, hashtags, and mentions

Article prose and feed text share URL, Unicode hashtag, and handle recognition and
link styling. External links open a new tab; hashtags open exact-tag search and
handles open profiles. Formatting boundaries do not split tokens. Code and existing
link marks are excluded from automatic recognition. Editing shows the same styling
without navigating on ordinary clicks, and decorations do not change stored JSON.

Typed mention nodes retain their account ID in JSON and display the current handle
from a public card. Requests are deduplicated, batched in groups of at most 50, and
cached for one minute. Missing accounts display "Account unavailable" without an ID.
Explicit hashtag blocks use ordinary hashtag links in article bodies.

## Code blocks

Code blocks use CodeBlockLowlight with the common Lowlight language set in both
editing and reading views. Enter a registered language or alias, such as `python`,
`javascript`, `typescript`, `json`, or `css`, in the block header. Language names
are recognized without case sensitivity. An empty or unsupported language displays
plain text; automatic language guessing is disabled. Copying returns only source
text, and syntax decorations are never stored in the article body.

Frontend dependency changes require rebuilding the frontend development image
before the next Docker Compose development run.

## Formulas and manual notes

Choose **LaTeX formula** from the block menu to insert a standalone equation. Its
source and preview appear together while editing; **Done** hides the source and
**Edit formula** opens it again. Formula blocks support the usual block movement
and deletion controls. Rendering errors display an escaped message and the source
inside that block; they do not discard input or prevent saving the rest of the
article. KaTeX runs with `trust: false` and bounded expansion and output size.

Use **Superscript** in the selection toolbar for manual notes such as `1` or `[1]`.
It is ordinary marked text, without automatic numbering or a generated note list.
Formula sources are not included in summaries, full-text search, or hashtag
extraction. Superscript text remains ordinary searchable and summarizable text.

The backend must support `blockMath` and `superscript` before deploying the frontend
that creates them. Existing article bodies require no migration.

## Header blocks and publishing

The header contains exactly one title and an optional cover. Drag the header grip
onto the other header block, use its up/down buttons, or press Alt+ArrowUp/ArrowDown
on the grip to change their order. Header blocks stay outside the body and cannot
be duplicated or moved into prose. Removing the cover leaves a compact add action
in the editor and no image placeholder on the published page or feed card.

The publishing dialog exposes the title, cover preview and controls, header order,
and schedule. Header and dialog controls edit the same state. **Save changes**,
**Publish now**, and **Schedule** save content and header settings before completing
any cover upload/removal and publication transition. Cover removal is staged until
saving. A failed upload or save retains pending input, stops the transition, and
can be retried without creating another draft. Covers are never required.

The `hero_layout` field defaults to `cover_title` for existing articles. No body
rewrite or database migration is needed.
