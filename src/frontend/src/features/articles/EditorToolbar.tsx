import { useCallback, useEffect, useState } from "react";
import type { RefObject } from "react";
import type { Editor } from "@tiptap/react";
import type { JSONContent } from "@tiptap/core";
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
}

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
  onAddImage: () => void;
  disabled: boolean;
}) {
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
    const first = editor.view.coordsAtPos(selection.from);
    const element = editor.view.nodeDOM(from);
    const top = element instanceof HTMLElement ? element.getBoundingClientRect().top : first.top;
    setPosition({
      top: Math.max(0, top - boundary.top), index, after: from + doc.child(index).nodeSize,
      selectionTop: first.top - boundary.top - 43, selectionLeft: Math.max(0, Math.min(first.left - boundary.left, boundary.width - 285)),
      selected: editor.isFocused && !selection.empty,
    });
  }, [editor, workspace]);

  useEffect(() => {
    if (!editor) return;
    const area = workspace.current;
    const observer = new ResizeObserver(update);
    if (area) observer.observe(area);
    editor.on("selectionUpdate", update).on("update", update).on("focus", update).on("blur", update);
    const frame = requestAnimationFrame(update);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      editor.off("selectionUpdate", update).off("update", update).off("focus", update).off("blur", update);
    };
  }, [editor, update, workspace]);

  if (!editor || !position || disabled) return null;

  function add(node: JSONContent) {
    if (!editor || !position) return;
    const { selection } = editor.state;
    if (selection.$from.depth === 1 && editor.isActive("paragraph") && selection.$from.parent.content.size === 0) {
      const from = selection.$from.before(1);
      editor.chain().insertContentAt({ from, to: position.after }, node).focus().run();
    } else {
      editor.chain().insertContentAt(position.after, node).focus().run();
    }
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

  const marks = [
    { label: "Bold", text: "B", active: editor.isActive("bold"), run: () => editor.chain().focus().toggleBold().run() },
    { label: "Italic", text: "I", active: editor.isActive("italic"), run: () => editor.chain().focus().toggleItalic().run() },
    { label: "Underline", text: "U", active: editor.isActive("underline"), run: () => editor.chain().focus().toggleUnderline().run() },
    { label: "Strike", text: "S", active: editor.isActive("strike"), run: () => editor.chain().focus().toggleStrike().run() },
  ];

  return <>
    <div className="block-tools" style={{ top: position.top }}>
      <button type="button" className="block-grip" aria-label="Reorder block" title="Drag to reorder"
        draggable onDragStart={(event) => {
          event.dataTransfer.setData(articleBlockDragType, String(position.index));
          event.dataTransfer.effectAllowed = "move";
          setMenu(undefined);
        }} onClick={() => setMenu(menu === "move" ? undefined : "move")}>
        <Icon name="grip" width={16} height={16} />
      </button>
      <button type="button" className="block-plus" aria-label="Add a block" aria-expanded={menu === "blocks"}
        onMouseDown={(event) => event.preventDefault()} onClick={() => setMenu(menu === "blocks" ? undefined : "blocks")}>
        <Icon name="plus" width={17} height={17} />
      </button>
    </div>
    {menu && <div className="block-menu" style={{ top: position.top + 29 }} onKeyDown={(event) => {
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
          onClick={() => { setMenu(undefined); onAddImage(); }}><Icon name="image" width={16} height={16} />Image</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("link"); }}><Icon name="link" width={16} height={16} />URL card</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("player"); }}><Icon name="play" width={16} height={16} />Embed</button>
        <button type="button" onClick={() => { setMenu(undefined); setRich("quote"); }}><Icon name="book" width={16} height={16} />Publication</button>
      </>}
    </div>}
    {rich && <div className="block-menu rich-block-menu" style={{ top: position.top + 29 }} onKeyDown={(event) => {
      if (event.key === "Escape") { setRich(undefined); editor.commands.focus(); }
    }}>
      <div className="block-menu-heading">Add rich content
        <button type="button" className="icon-button" aria-label="Close rich content" onClick={() => setRich(undefined)}><Icon name="close" width={15} height={15} /></button>
      </div>
      <AttachmentComposer initialMode={rich} onAdd={(descriptor) => add({ type: "attachment", attrs: { descriptor } })} />
    </div>}
    {position.selected && !menu && !rich && <div className="selection-bubble" role="toolbar" aria-label="Text formatting"
      style={{ top: position.selectionTop, left: position.selectionLeft }}>
      <select aria-label="Text style" value={editor.isActive("heading") ? String(editor.getAttributes("heading").level) : "paragraph"}
        onChange={(event) => {
          const value = event.currentTarget.value;
          if (value === "paragraph") editor.chain().focus().setParagraph().run();
          else if (value === "1" || value === "2" || value === "3") {
            editor.chain().focus().setHeading({ level: Number(value) as 1 | 2 | 3 }).run();
          }
        }}>
        <option value="paragraph">Text</option><option value="1">Header 1</option><option value="2">Header 2</option><option value="3">Header 3</option>
      </select>
      {marks.map(({ label, text, active, run }) => <button type="button" key={label} aria-label={label}
        aria-pressed={active} title={label} onMouseDown={(event) => event.preventDefault()} onClick={run}>{text}</button>)}
      <button type="button" aria-label="Link" title="Link" onMouseDown={(event) => event.preventDefault()} onClick={() => {
        const value = window.prompt("Link URL", editor.getAttributes("link").href || "https://");
        if (value === null) return;
        const chain = editor.chain().focus().extendMarkRange("link");
        if (value.trim()) chain.setLink({ href: value.trim() }).run();
        else chain.unsetLink().run();
      }}><Icon name="link" width={16} height={16} /></button>
      <select aria-label="Text alignment" value="" onChange={(event) => {
        const type = editor.isActive("heading") ? "heading" : "paragraph";
        editor.chain().focus().updateAttributes(type, { textAlign: event.currentTarget.value }).run();
      }}>
        <option value="" disabled>Align</option><option value="left">Left</option><option value="center">Center</option>
        <option value="right">Right</option><option value="justify">Justify</option>
      </select>
    </div>}
  </>;
}
