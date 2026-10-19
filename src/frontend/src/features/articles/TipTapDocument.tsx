import type { JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import { createEditorExtensions } from "./editorExtensions";
import { useEffect } from "react";
import { fromEditorBody, toEditorBody } from "./contentNodes";
export function TipTapDocument({ body, editable = false, onChange }: {
  body: JSONContent;
  editable?: boolean;
  onChange?: (body: JSONContent) => void;
}) {
  const editor = useEditor({
    extensions: createEditorExtensions(editable),
    content: toEditorBody(body),
    editable,
    onUpdate: ({ editor: current }) => onChange?.(fromEditorBody(current.getJSON())),
    editorProps: { attributes: { class: `tiptap-content ${editable ? "tiptap-editable" : ""}` } },
  });
  useEffect(() => {
    if (editor && JSON.stringify(fromEditorBody(editor.getJSON())) !== JSON.stringify(body))
      editor.commands.setContent(toEditorBody(body), { emitUpdate: false });
  }, [editor, body]);
  return <EditorContent editor={editor} />;
}
