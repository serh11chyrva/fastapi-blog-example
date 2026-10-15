import type { Editor } from "@tiptap/react";
export function EditorToolbar({ editor, onAddImage }: {
  editor: Editor | null;
  onAddImage?: () => void;
}) {
  const actions: {
    label: string;
    run: () => void;
    active?: boolean;
  }[] = editor ? [
    { label: "B", run: () => editor.chain().focus().toggleBold().run(), active: editor.isActive("bold") },
    { label: "I", run: () => editor.chain().focus().toggleItalic().run(), active: editor.isActive("italic") },
    { label: "S", run: () => editor.chain().focus().toggleStrike().run(), active: editor.isActive("strike") },
    { label: "H1", run: () => editor.chain().focus().toggleHeading({ level: 1 }).run(), active: editor.isActive("heading", { level: 1 }) },
    { label: "H2", run: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active: editor.isActive("heading", { level: 2 }) },
    { label: "H3", run: () => editor.chain().focus().toggleHeading({ level: 3 }).run(), active: editor.isActive("heading", { level: 3 }) },
    { label: "• List", run: () => editor.chain().focus().toggleBulletList().run(), active: editor.isActive("bulletList") },
    { label: "1. List", run: () => editor.chain().focus().toggleOrderedList().run(), active: editor.isActive("orderedList") },
    { label: "Quote", run: () => editor.chain().focus().toggleBlockquote().run(), active: editor.isActive("blockquote") },
    { label: "Code", run: () => editor.chain().focus().toggleCodeBlock().run(), active: editor.isActive("codeBlock") },
    {
      label: "Link", run: () => {
        const current = editor.getAttributes("link").href as string | undefined; const href = window.prompt("Link URL", current || "https://"); if (href === null)
          return; if (href.trim())
          editor.chain().focus().extendMarkRange("link").setLink({ href: href.trim() }).run();
        else
          editor.chain().focus().extendMarkRange("link").unsetLink().run();
      }, active: editor.isActive("link")
    },
    ...(onAddImage ? [{ label: "Image", run: onAddImage }] : []),
  ] : [];
  return <div className="mt-5 flex flex-wrap gap-1 rounded-t-xl border border-slate-200 bg-slate-50 p-2">
    {actions.map((action) => <button key={action.label} type="button" onClick={action.run} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${action.active ? "bg-slate-100 text-slate-700" : "text-slate-600 hover:bg-white"}`}>
      {action.label}
    </button>)}
  </div>;
}
