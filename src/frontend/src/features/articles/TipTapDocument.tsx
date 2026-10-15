import type { JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import { createEditorExtensions } from "./editorExtensions";
import { useEffect } from "react";
export function TipTapDocument({ body, editable = false, onChange }: {
  body: JSONContent;
  editable?: boolean;
  onChange?: (body: JSONContent) => void;
}) {
  const editor = useEditor({
    extensions: createEditorExtensions(),
    content: body,
    editable,
    onUpdate: ({ editor: current }) => onChange?.(current.getJSON()),
    editorProps: { attributes: { class: `tiptap-content ${editable ? "tiptap-editable" : ""}` } },
  });
  useEffect(() => {
    if (editor && JSON.stringify(editor.getJSON()) !== JSON.stringify(body))
      editor.commands.setContent(body);
  }, [editor, body]);
  return <EditorContent editor={editor} />;
}
