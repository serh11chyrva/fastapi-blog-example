import { useId, useRef, useState } from "react";
import type { ProfileLinkInput } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";

export type ProfileLinkDraft = { key: string; link: ProfileLinkInput };

export function ProfileLinksEditor({ links, onChange }: {
  links: ProfileLinkDraft[];
  onChange: (links: ProfileLinkDraft[]) => void;
}) {
  const list = useRef<HTMLDivElement>(null);
  const nextKey = useRef(0);
  const instructions = useId();
  const [dropTarget, setDropTarget] = useState<string>();
  const [announcement, setAnnouncement] = useState("");

  function linkAt(x: number, y: number) {
    const row = document.elementFromPoint(x, y)?.closest<HTMLElement>("[data-profile-link]");
    return row && list.current?.contains(row) ? row.dataset.profileLink : undefined;
  }

  function move(from: number, to: number) {
    if (from === to || to < 0 || to >= links.length) return;
    const reordered = [...links];
    const [item] = reordered.splice(from, 1);
    reordered.splice(to, 0, item);
    onChange(reordered);
    setAnnouncement(`${item.link.label || "Link"} moved to position ${to + 1} of ${links.length}.`);
  }

  function update(key: string, field: "label" | "url", value: string) {
    onChange(links.map((item) => item.key === key ? { ...item, link: { ...item.link, [field]: value } } : item));
  }

  return <section className="space-y-2" aria-label="Profile links">
    <h2 className="form-label">Profile links</h2>
    {links.length > 1 && <p id={instructions} className="profile-links-hint">
      Drag a handle or focus it and use the arrow keys to reorder links.
    </p>}
    <div className="space-y-2" ref={list}>
      {links.map(({ key, link }, index) => <div className="profile-link-row" key={key}
        data-profile-link={key} data-drop-target={dropTarget === key || undefined}>
        <button type="button" className="icon-button profile-link-grip" aria-label={`Reorder link ${index + 1}`}
          aria-describedby={links.length > 1 ? instructions : undefined} disabled={links.length < 2}
          onPointerDown={(event) => {
            if (event.button === 0 && event.isPrimary) event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
            const target = linkAt(event.clientX, event.clientY);
            setDropTarget(target === key ? undefined : target);
          }}
          onPointerUp={(event) => {
            if (event.currentTarget.hasPointerCapture(event.pointerId)) {
              const target = linkAt(event.clientX, event.clientY);
              move(index, links.findIndex((item) => item.key === target));
            }
          }}
          onLostPointerCapture={() => setDropTarget(undefined)}
          onKeyDown={(event) => {
            if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
            event.preventDefault();
            move(index, index + (event.key === "ArrowUp" ? -1 : 1));
          }}>
          <Icon name="grip" />
        </button>
        <input className="field" aria-label={`Link ${index + 1} label`} placeholder="Label" maxLength={32}
          value={link.label} onChange={(event) => update(key, "label", event.target.value)} />
        <input className="field" aria-label={`Link ${index + 1} URL`} type="url" placeholder="https://example.com" maxLength={500}
          value={link.url} onChange={(event) => update(key, "url", event.target.value)} />
        <button type="button" className="button-quiet" aria-label={`Remove link ${index + 1}`}
          onClick={() => onChange(links.filter((item) => item.key !== key))}>Remove</button>
      </div>)}
    </div>
    <p className="sr-only" role="status">{announcement}</p>
    <button type="button" className="button-secondary" disabled={links.length >= 8} onClick={() => {
      onChange([...links, { key: `new-${nextKey.current++}`, link: { label: "", url: "https://" } }]);
    }}><Icon name="plus" width={15} height={15} />Add link</button>
  </section>;
}
