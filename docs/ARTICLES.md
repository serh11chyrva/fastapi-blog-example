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
