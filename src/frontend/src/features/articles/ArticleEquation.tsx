import { useMemo, useState } from "react";
import { BlockMath } from "@tiptap/extension-mathematics";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import katex from "katex";

const renderingOptions = { displayMode: true, trust: false, throwOnError: true, maxExpand: 1000, maxSize: 20 };

function EquationView({ editor, node, updateAttributes, selected }: NodeViewProps) {
  const latex = String(node.attrs.latex ?? "");
  const [editing, setEditing] = useState(!latex);
  const preview = useMemo(() => {
    if (!latex.trim()) return { html: "", error: "" };
    try { return { html: katex.renderToString(latex, renderingOptions), error: "" }; }
    catch (reason) { return { html: "", error: reason instanceof Error ? reason.message : "Could not render this formula." }; }
  }, [latex]);

  return <NodeViewWrapper contentEditable={false} className={`equation-node${selected ? " is-selected" : ""}`}>
    {editor.isEditable && <div className="embed-bar"><span>LaTeX formula</span>
      <button type="button" aria-expanded={editing} onClick={() => setEditing(!editing)}>{editing ? "Done" : "Edit formula"}</button>
    </div>}
    {editor.isEditable && editing && <label className="equation-source">LaTeX source
      <textarea className="field" aria-label="LaTeX source" rows={3} value={latex} spellCheck={false}
        onChange={(event) => updateAttributes({ latex: event.target.value })}
        onKeyDown={(event) => {
          if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setEditing(false); editor.commands.focus(); }
        }} />
    </label>}
    {preview.html ? <div className="equation-preview" dangerouslySetInnerHTML={{ __html: preview.html }} />
      : <div className="equation-preview equation-fallback">
        {preview.error ? <><p className="equation-error" role="alert">{preview.error}</p><pre>{latex}</pre></>
          : <span>Enter a LaTeX formula</span>}
      </div>}
  </NodeViewWrapper>;
}

export const ArticleEquation = BlockMath.extend({
  draggable: true,
  addNodeView() { return ReactNodeViewRenderer(EquationView); },
}).configure({ katexOptions: renderingOptions });
