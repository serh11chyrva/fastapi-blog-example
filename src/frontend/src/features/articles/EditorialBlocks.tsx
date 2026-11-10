import { useState } from "react";
import Blockquote from "@tiptap/extension-blockquote";
import CodeBlock from "@tiptap/extension-code-block";
import { NodeViewContent, NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import { Icon } from "../../shared/ui/Icon";

function QuoteBlock({ editor, node, updateAttributes }: NodeViewProps) {
  const citation = String(node.attrs.citation ?? "");
  return <NodeViewWrapper as="blockquote" className="editorial-quote">
    <div className="quote-line">
      <span contentEditable={false} aria-hidden="true">«</span>
      <NodeViewContent as="div" />
      <span contentEditable={false} aria-hidden="true">»</span>
    </div>
    {editor.isEditable
      ? <cite contentEditable={false}><input aria-label="Quote citation" placeholder="Add a citation" value={citation}
          maxLength={200} onChange={(event) => updateAttributes({ citation: event.target.value || null })} /></cite>
      : citation && <cite contentEditable={false}>— {citation}</cite>}
  </NodeViewWrapper>;
}

function CodeBlockView({ editor, node, updateAttributes }: NodeViewProps) {
  const [status, setStatus] = useState("");
  const language = String(node.attrs.language ?? "");
  async function copy() {
    try {
      await navigator.clipboard.writeText(node.textContent);
      setStatus("Copied");
    } catch { setStatus("Could not copy"); }
  }
  return <NodeViewWrapper as="figure" className="code-embed">
    <figcaption contentEditable={false} className="embed-bar">
      <span><Icon name="code" width={16} height={16} /> Code</span>
      {editor.isEditable ? <input aria-label="Code language" maxLength={32} placeholder="Language" value={language}
        onChange={(event) => {
          const value = event.target.value;
          if (/^[a-z\d_+.#-]*$/i.test(value)) updateAttributes({ language: value || null });
        }} /> : <>
        <span>{language || "Plain text"}</span>
        <button type="button" onClick={() => void copy()}>{status || "Copy code"}</button>
      </>}
    </figcaption>
    <pre><NodeViewContent<"code"> as="code" className={language ? `language-${language}` : undefined} /></pre>
  </NodeViewWrapper>;
}

export const EditorialQuote = Blockquote.extend({
  addAttributes() {
    return { ...this.parent?.(), citation: { default: null } };
  },
  addNodeView() { return ReactNodeViewRenderer(QuoteBlock); },
});

export const EditorialCode = CodeBlock.extend({
  addNodeView() { return ReactNodeViewRenderer(CodeBlockView); },
});
