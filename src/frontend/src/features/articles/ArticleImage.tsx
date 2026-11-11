import { Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import { Icon } from "../../shared/ui/Icon";

export const replaceArticleImageEvent = "article-image-replace";

function ImageView({ editor, node, getPos, updateAttributes, deleteNode, selected }: NodeViewProps) {
  return <NodeViewWrapper as="figure" className={`article-image-node ${selected ? "is-selected" : ""}`} contentEditable={false}>
    <img src={node.attrs.src} alt={node.attrs.alt ?? ""} title={node.attrs.title || undefined} loading="lazy" />
    {editor.isEditable ? <div className="article-image-controls">
      <label>Alternative text<input value={node.attrs.alt ?? ""} maxLength={1000}
        onChange={(event) => updateAttributes({ alt: event.target.value })} /></label>
      <label>Caption<input value={node.attrs.title ?? ""} maxLength={1000}
        onChange={(event) => updateAttributes({ title: event.target.value || null })} /></label>
      <div>
        <button type="button" className="button-quiet" onClick={() => {
          const from = getPos();
          if (typeof from === "number") editor.view.dom.dispatchEvent(new CustomEvent(replaceArticleImageEvent, {
            detail: { from, to: from + node.nodeSize, alt: node.attrs.alt ?? "", title: node.attrs.title ?? null },
          }));
        }}><Icon name="image" /> Replace image</button>
        <button type="button" className="button-quiet" onClick={deleteNode}><Icon name="close" /> Remove image</button>
      </div>
    </div> : node.attrs.title && <figcaption>{node.attrs.title}</figcaption>}
  </NodeViewWrapper>;
}

export const ArticleImage = Node.create({
  name: "image", group: "block", atom: true, draggable: true,
  addAttributes() { return { src: { default: null }, alt: { default: "" }, title: { default: null } }; },
  parseHTML() { return [{ tag: "img[src]" }]; },
  renderHTML({ HTMLAttributes }) { return ["img", { ...HTMLAttributes, loading: "lazy" }]; },
  addNodeView() { return ReactNodeViewRenderer(ImageView); },
});
