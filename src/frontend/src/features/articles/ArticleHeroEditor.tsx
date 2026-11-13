import type { ReactNode } from "react";
import type { HeroLayout } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";

const heroDragType = "application/x-blog-article-hero";

export function ArticleCoverControl({ preview, disabled, onChoose, onRemove }: {
  preview?: string | null; disabled: boolean; onChoose: (file: File) => void; onRemove: () => void;
}) {
  const input = <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" disabled={disabled}
    onChange={(event) => { const file = event.target.files?.[0]; if (file) onChoose(file); event.target.value = ""; }} />;
  return preview ? <figure className="article-cover writer-cover">
    <img src={preview} alt="Article cover preview" draggable={false} />
    <div className="cover-edit">
      <label className="cover-change">Change cover{input}</label>
      <button type="button" className="cover-change" aria-label="Remove cover" disabled={disabled} onClick={onRemove}>
        <Icon name="close" width={16} height={16} />
      </button>
    </div>
  </figure> : <label className="add-cover"><Icon name="plus" width={17} height={17} />Add a cover (optional){input}</label>;
}

export function ArticleHeroEditor({ title, onTitleChange, layout, onLayoutChange, cover, disabled, onEnterBody }: {
  title: string; onTitleChange: (value: string) => void; layout: HeroLayout;
  onLayoutChange: (value: HeroLayout) => void; cover: ReactNode; disabled: boolean; onEnterBody: () => void;
}) {
  const order = layout === "cover_title" ? ["cover", "title"] as const : ["title", "cover"] as const;
  const swapped = layout === "cover_title" ? "title_cover" : "cover_title";
  return <header className="writer-hero">{order.map((kind, index) => <div key={kind} className={`hero-block hero-${kind}`}
    onDragOver={(event) => {
      if (!disabled && event.dataTransfer.types.includes(heroDragType)) {
        event.preventDefault(); event.stopPropagation(); event.dataTransfer.dropEffect = "move";
      }
    }} onDrop={(event) => {
      const source = event.dataTransfer.getData(heroDragType);
      if (disabled || !source) return;
      event.preventDefault(); event.stopPropagation();
      if (source !== kind && order.includes(source as typeof kind)) onLayoutChange(swapped);
    }}>
    <div className="hero-block-tools" role="group" aria-label={`${kind === "title" ? "Title" : "Cover"} block controls`}>
      <button type="button" className="icon-button" disabled={disabled} draggable={!disabled}
        aria-label={`Reorder ${kind} block`} title={`Drag ${kind} block to reorder`}
        onDragStart={(event) => { event.dataTransfer.setData(heroDragType, kind); event.dataTransfer.effectAllowed = "move"; }}
        onKeyDown={(event) => {
          if (event.altKey && ((event.key === "ArrowUp" && index === 1) || (event.key === "ArrowDown" && index === 0))) {
            event.preventDefault(); onLayoutChange(swapped);
          }
        }}><Icon name="grip" width={16} height={16} /></button>
      <button type="button" className="icon-button hero-move-up" disabled={disabled || index === 0}
        aria-label={`Move ${kind} block up`} title="Move up" onClick={() => onLayoutChange(swapped)}><Icon name="chevron" /></button>
      <button type="button" className="icon-button" disabled={disabled || index === 1}
        aria-label={`Move ${kind} block down`} title="Move down" onClick={() => onLayoutChange(swapped)}><Icon name="chevron" /></button>
    </div>
    {kind === "cover" ? cover : <textarea aria-label="Article title" className="writer-title" disabled={disabled} maxLength={160}
      placeholder="Untitled" rows={1} value={title} onChange={(event) => onTitleChange(event.target.value)}
      onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); onEnterBody(); } }} />}
  </div>)}</header>;
}
