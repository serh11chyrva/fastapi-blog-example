# Platform icons

The SVG paths in `paths.ts` are vendored from
[Simple Icons 11.15.0](https://github.com/simple-icons/simple-icons/tree/11.15.0/icons).
Only the 29 profile platforms recognized by the backend are included. All paths use
the original 24 x 24 viewBox and are rendered in black, without brand colors.
No external icon requests are made at runtime.

Upstream filenames match the platform identifiers except for `apple_music`
(`applemusic.svg`), `itch_io` (`itchdotio.svg`), and `ko_fi` (`kofi.svg`).
The pinned [upstream metadata](https://github.com/simple-icons/simple-icons/blob/11.15.0/_data/simple-icons.json)
records the original brand sources and any individual license information.

Simple Icons is a CC0 project; its license is included in [LICENSE.txt](LICENSE.txt).
Brand marks belong to their respective owners; see the
[upstream disclaimer](https://github.com/simple-icons/simple-icons/blob/11.15.0/DISCLAIMER.md)
and the original brand sources for individual guidance. Vendoring does not imply
endorsement by these platforms.

When adding a backend platform, add its icon path and provenance here. Keep
`website` and unknown identifiers on the generic link fallback in `ProfileLinkIcon`.
