import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import type { Editor } from "@tiptap/react";
import type { JSONContent } from "@tiptap/core";
import type { Transaction } from "@tiptap/pm/state";
import { Icon } from "../../shared/ui/Icon";
import { AttachmentComposer } from "../publications/AttachmentComposer";

export const articleBlockDragType = "application/x-blog-article-block";

export function moveArticleBlock(editor: Editor, source: number, target: number) {
  const blocks: { from: number; node: typeof editor.state.doc }[] = [];
  editor.state.doc.forEach((node, from) => blocks.push({ node, from }));
  const moving = blocks[source];
  const destination = blocks[target];
  if (!moving || !destination || source === target) return;
  const { tr } = editor.state;
  const position = source < target ? destination.from + destination.node.nodeSize - moving.node.nodeSize : destination.from;
  editor.view.dispatch(tr.delete(moving.from, moving.from + moving.node.nodeSize).insert(position, moving.node));
  editor.commands.focus();
  editor.commands.setTextSelection(Math.min(position + 1, editor.state.doc.content.size));
}

export type InsertionRange = { from: number; to: number };
type ToolsPosition = { top: number; index: number; after: number; selectionTop: number; selectionLeft: number; selected: boolean };

const blocks: { label: string; glyph: string; node: JSONContent }[] = [
  { label: "Text", glyph: "T", node: { type: "paragraph" } },
  ...([1, 2, 3] as const).map((level) => ({ label: `Header ${level}`, glyph: `H${level}`, node: { type: "heading", attrs: { level } } })),
  { label: "Quote", glyph: "«", node: { type: "blockquote", content: [{ type: "paragraph" }] } },
  { label: "Bulleted list", glyph: "•", node: { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph" }] }] } },
  { label: "Numbered list", glyph: "1.", node: { type: "orderedList", content: [{ type: "listItem", content: [{ type: "paragraph" }] }] } },
  { label: "Code", glyph: "</>", node: { type: "codeBlock" } },
  { label: "Divider", glyph: "—", node: { type: "horizontalRule" } },
];

export function EditorToolbar({ editor, workspace, onAddImage, disabled }: {
  editor: Editor | null;
  workspace: RefObject<HTMLDivElement | null>;
  onAddImage: (range: InsertionRange) => void;
  disabled: boolean;
}) {
  const insertion = useRef<InsertionRange | null>(null);
  const selection = useRef<InsertionRange | null>(null);
  const [gaps, setGaps] = useState<{ top: number; from: number }[]>([]);
  const [menuTop, setMenuTop] = useState(0);
  const [link, setLink] = useState<string | null>(null);
  const [linkError, setLinkError] = useState("");
  const [position, setPosition] = useState<ToolsPosition>();
  const [menu, setMenu] = useState<"blocks" | "move">();
  const [rich, setRich] = useState<"link" | "player" | "quote">();
  const update = useCallback(() => {
    const area = workspace.current;
    if (!editor || !area || editor.isDestroyed) return;
    const { selection, doc } = editor.state;
    const index = Math.min(selection.$from.index(0), doc.childCount - 1);
    if (index < 0) return;
    let from = 0;
    for (let cursor = 0; cursor < index; cursor++) from += doc.child(cursor).nodeSize;
    const boundary = area.getBoundingClientRect();
    const nextGaps: { top: number; from: number }[] = [];
    doc.forEach((node, offset) => {
      const element = editor.view.nodeDOM(offset);
      if (element instanceof HTMLElement) {
        const rect = element.getBoundingClientRect();
        nextGaps.push({ top: rect.top - boundary.top - 8, from: offset });
        if (offset + node.nodeSize === doc.content.size) nextGaps.push({ top: rect.bottom - boundary.top + 12, from: doc.content.size });
      }
    });
    setGaps(nextGaps);
    const first = editor.view.coordsAtPos(selection.from);
    const element = editor.view.nodeDOM(from);
    const top = element instanceof HTMLElement ? element.getBoundingClientRect().top : first.top;
    setPosition({
      top: Math.max(0, top - boundary.top), index, after: from + doc.child(index).nodeSize,
      selectionTop: first.top - boundary.top - 43, selectionLeft: Math.max(0, Math.min(first.left - boundary.left, boundary.width - 285)),
      selected: !selection.empty && !editor.isActive("codeBlock"),
    });
  }, [editor, workspace]);

  useEffect(() => {
    if (!editor) return;
    const area = workspace.current;
    const observer = new ResizeObserver(update);
    if (area) observer.observe(area);
    editor.on("selectionUpdate", update).on("update", update).on("focus", update).on("blur", update);
    const frame = requestAnimationFrame(update);
    function mapPositions({ transaction }: { transaction: Transaction }) {
      if (insertion.current) insertion.current = {
        from: transaction.mapping.map(insertion.current.from, -1), to: transaction.mapping.map(insertion.current.to, 1),
      };
      if (!transaction.selection.empty) selection.current = { from: transaction.selection.from, to: transaction.selection.to };
    }
    function keydown(event: KeyboardEvent) {
      if (!editor || disabled) return;
      const current = editor.state.selection;
      if (event.key === "/" && current.empty && current.$from.parent.type.name === "paragraph" && !current.$from.parent.textContent) {
        event.preventDefault(); event.stopPropagation();
        insertion.current = { from: current.$from.before(), to: current.$from.after() };
        const area = workspace.current!.getBoundingClientRect();
        setMenuTop(editor.view.coordsAtPos(current.from).top - area.top + 25);
        setMenu("blocks");
      }
      if (event.altKey && ["ArrowUp", "ArrowDown"].includes(event.key)) {
        event.preventDefault(); event.stopPropagation();
        const index = current.$from.index(0);
        moveArticleBlock(editor, index, index + (event.key === "ArrowUp" ? -1 : 1));
      }
      if (event.key === "Escape") { setMenu(undefined); setRich(undefined); setLink(null); }
    }
    editor.on("transaction", mapPositions);
    editor.view.dom.addEventListener("keydown", keydown, true);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      editor.off("transaction", mapPositions);
      editor.view.dom.removeEventListener("keydown", keydown, true);
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
      cancelAnimationFrame(frame);
      editor.off("selectionUpdate", update).off("update", update).off("focus", update).off("blur", update);
    };
  }, [editor, update, workspace, disabled]);

  if (!editor || !position || disabled) return null;

  function add(node: JSONContent) {
    if (!editor || !position) return;
    const range = insertion.current ?? { from: position.after, to: position.after };
    insertion.current = null;
    const atomic = ["attachment", "image", "horizontalRule"].includes(node.type ?? "");
    editor.chain().focus().insertContentAt(range, atomic ? [node, { type: "paragraph" }] : node).run();
    const inserted = editor.state.doc.nodeAt(range.from);
    const offset = atomic ? (inserted?.nodeSize ?? 1) + 1 : ["blockquote"].includes(node.type ?? "") ? 2
      : ["bulletList", "orderedList"].includes(node.type ?? "") ? 3 : 1;
    editor.commands.setTextSelection(Math.min(range.from + offset, editor.state.doc.content.size));
    setMenu(undefined);
    setRich(undefined);
  }

  function deleteBlock() {
    if (!editor || !position) return;
    const child = editor.state.doc.child(position.index);
    const from = position.after - child.nodeSize;
    if (editor.state.doc.childCount === 1) editor.commands.clearContent(true);
    else editor.commands.deleteRange({ from, to: position.after });
    editor.commands.focus();
    setMenu(undefined);
  }

  function chain() {
    const current = editor!.chain().focus();
    return selection.current ? current.setTextSelection(selection.current) : current;
  }

  const marks = [
    { label: "Bold", text: "B", active: editor.isActive("bold"), run: () => chain().toggleBold().run() },
    { label: "Italic", text: "I", active: editor.isActive("italic"), run: () => chain().toggleItalic().run() },
    { label: "Underline", text: "U", active: editor.isActive("underline"), run: () => chain().toggleUnderline().run() },
    { label: "Strike", text: "S", active: editor.isActive("strike"), run: () => chain().toggleStrike().run() },
  ];

  return <>
    {gaps.map((gap) => <div key={gap.from} className="editor-insert-gap" style={{ top: gap.top }}>
      <button type="button" aria-label={gap.from === 0 ? "Insert before first block" : "Insert block here"}
        onMouseDown={(event) => event.preventDefault()} onClick={() => {
          const node = editor.state.doc.nodeAt(gap.from);
          insertion.current = { from: gap.from, to: node?.type.name === "paragraph" && !node.content.size ? gap.from + node.nodeSize : gap.from };
          setMenuTop(gap.top + 24); setRich(undefined); setMenu("blocks");
        }}><Icon name="plus" width={17} height={17} /></button>
    </div>)}
    <div className="block-tools" style={{ top: position.top }}>
      <button type="button" className="block-grip" aria-label="Reorder block" title="Drag to reorder"
        draggable onDragStart={(event) => {
          event.dataTransfer.setData(articleBlockDragType, String(position.index));
          event.dataTransfer.effectAllowed = "move";
          setMenu(undefined);
        }} onClick={() => (setMenuTop(position.top + 29), setMenu(menu === "move" ? undefined : "move"))}>
        <Icon name="grip" width={16} height={16} />
      </button>
      <button type="button" className="block-plus" aria-label="Add a block" aria-expanded={menu === "blocks"}
        onMouseDown={(event) => event.preventDefault()} onClick={() => {
          const current = editor.state.selection;
          insertion.current = current.$from.depth === 1 && current.$from.parent.type.name === "paragraph" && !current.$from.parent.content.size
            ? { from: current.$from.before(), to: current.$from.after() } : { from: position.after, to: position.after };
          setMenuTop(position.top + 29); setMenu(menu === "blocks" ? undefined : "blocks");
        }}>
        <Icon name="plus" width={17} height={17} />
      </button>
    </div>
    {menu && <div className="block-menu" style={{ top: menuTop, maxHeight: Math.max(120, window.innerHeight - (workspace.current?.getBoundingClientRect().top ?? 0) - menuTop - 12), overflowY: "auto" }} onKeyDown={(event) => {
      if (event.key === "Escape") { setMenu(undefined); editor.commands.focus(); }
    }}>
      <div className="block-menu-heading">{menu === "move" ? "Block options" : "Add a block"}
        <button type="button" className="icon-button" aria-label="Close block menu" onClick={() => setMenu(undefined)}><Icon name="close" width={15} height={15} /></button>
      </div>
      {menu === "move" ? <>
        <button type="button" disabled={position.index === 0} onClick={() => { moveArticleBlock(editor, position.index, position.index - 1); setMenu(undefined); }}>Move up</button>
        <button type="button" disabled={position.index === editor.state.doc.childCount - 1}
          onClick={() => { moveArticleBlock(editor, position.index, position.index + 1); setMenu(undefined); }}>Move down</button>
        <button type="button" onClick={deleteBlock}>Delete block</button>
      </> : <>
        {blocks.map(({ label, glyph, node }) => <button type="button" key={label}
          onMouseDown={(event) => event.preventDefault()} onClick={() => add(node)}><span>{glyph}</span>{label}</button>)}
        <button type="button" onMouseDown={(event) => event.preventDefault()}
          onClick={() => { setMenu(undefined); onAddImage(insertion.current ?? { from: position.after, to: position.after }); insertion.current = null; }}><Icon name="image" width={16} height={16} />Image</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("link"); }}><Icon name="link" width={16} height={16} />URL card</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("player"); }}><Icon name="play" width={16} height={16} />Embed</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("quote"); }}><Icon name="book" width={16} height={16} />Publication</button>
      </>}
    </div>}
    {rich && <div className="block-menu rich-block-menu" style={{ top: menuTop, maxHeight: Math.max(120, window.innerHeight - (workspace.current?.getBoundingClientRect().top ?? 0) - menuTop - 12), overflowY: "auto" }} onKeyDown={(event) => {
      if (event.key === "Escape") { setRich(undefined); editor.commands.focus(); }
    }}>
      <div className="block-menu-heading">Add rich content
        <button type="button" className="icon-button" aria-label="Close rich content" onClick={() => setRich(undefined)}><Icon name="close" width={15} height={15} /></button>
      </div>
      <AttachmentComposer initialMode={rich} onAdd={(descriptor) => add({ type: "attachment", attrs: { descriptor } })} />
    </div>}
    {link !== null && <form className="block-menu rich-block-menu" style={{ top: Math.max(0, position.top + 30) }}
      onSubmit={(event) => {
        event.preventDefault();
        try {
          if (link.trim()) {
            const url = new URL(link.trim());
            if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error("Use an HTTP or HTTPS link.");
            chain().extendMarkRange("link").setLink({ href: url.href }).run();
          } else chain().extendMarkRange("link").unsetLink().run();
          setLink(null);
        } catch { setLinkError("Use a valid HTTP or HTTPS URL without credentials."); }
      }}>
      <label className="form-label">Link URL<input className="field" autoFocus value={link} onChange={(event) => setLink(event.target.value)} /></label>
      <button className="button-primary">Apply link</button>
      <button type="button" onClick={() => { chain().extendMarkRange("link").unsetLink().run(); setLink(null); }}>Remove link</button>
      <button type="button" onClick={() => { setLink(null); editor.commands.focus(); }}>Cancel</button>
      {linkError && <p role="alert">{linkError}</p>}
    </form>}
    {position.selected && !menu && !rich && link === null && <div className="selection-bubble" role="toolbar" aria-label="Text formatting"
      style={{ top: position.selectionTop, left: position.selectionLeft }}>
      <select aria-label="Text style" value={editor.isActive("heading") ? String(editor.getAttributes("heading").level) : "paragraph"}
        onChange={(event) => {
          const value = event.currentTarget.value;
          if (value === "paragraph") chain().setParagraph().run();
          else if (value === "1" || value === "2" || value === "3") {
            chain().setHeading({ level: Number(value) as 1 | 2 | 3 }).run();
          }
        }}>
        <option value="paragraph">Text</option><option value="1">Header 1</option><option value="2">Header 2</option><option value="3">Header 3</option>
      </select>
      {marks.map(({ label, text, active, run }) => <button type="button" key={label} aria-label={label}
        aria-pressed={active} title={label} onMouseDown={(event) => event.preventDefault()} onClick={run}>{text}</button>)}
      <button type="button" aria-label="Link" title="Link" onMouseDown={(event) => event.preventDefault()} onClick={() => {
        selection.current = { from: editor.state.selection.from, to: editor.state.selection.to };
        setLink(editor.getAttributes("link").href || "https://"); setLinkError("");
      }}><Icon name="link" width={16} height={16} /></button>
      <select aria-label="Text alignment" value="" onChange={(event) => {
        const type = editor.isActive("heading") ? "heading" : "paragraph";
        chain().updateAttributes(type, { textAlign: event.currentTarget.value }).run();
      }}>
        <option value="" disabled>Align</option><option value="left">Left</option><option value="center">Center</option>
        <option value="right">Right</option><option value="justify">Justify</option>
      </select>
    </div>}
  </>;
}
