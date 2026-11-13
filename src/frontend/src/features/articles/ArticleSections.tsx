import { Extension } from "@tiptap/core";
import type { Editor } from "@tiptap/react";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { useEffect, useState } from "react";

type ArticleSection = { id: string; label: string; position: number };

function sectionsIn(editor: Editor): ArticleSection[] {
  const sections: ArticleSection[] = [];
  editor.state.doc.descendants((node, position) => {
    if (node.type.name === "heading" && node.textContent.trim()) {
      sections.push({ id: `section-${sections.length + 1}`, label: node.textContent.trim(), position });
    }
  });
  return sections;
}

export const ArticleSectionAnchors = Extension.create({
  name: "articleSectionAnchors",
  addProseMirrorPlugins() {
    return [new Plugin({
      props: {
        decorations(state) {
          const anchors: Decoration[] = [];
          state.doc.descendants((node, position) => {
            if (node.type.name === "heading" && node.textContent.trim()) {
              anchors.push(Decoration.node(position, position + node.nodeSize, { id: `section-${anchors.length + 1}` }));
            }
          });
          return DecorationSet.create(state.doc, anchors);
        },
      },
    })];
  },
});

export function ArticleSectionNavigation({ editor }: { editor: Editor | null }) {
  const [sections, setSections] = useState<ArticleSection[]>([]);
  const [current, setCurrent] = useState<string>();

  useEffect(() => {
    if (!editor) return;
    function refresh() {
      if (editor && !editor.isDestroyed) setSections(sectionsIn(editor));
    }
    refresh();
    editor.on("transaction", refresh);
    return () => { editor.off("transaction", refresh); };
  }, [editor]);

  useEffect(() => {
    if (!editor || !sections.length) return;
    function update() {
      if (!editor || editor.isDestroyed) return;
      const active = sections.filter(({ position }) => {
        const element = editor.view.nodeDOM(position);
        return element instanceof HTMLElement && element.getBoundingClientRect().top < 150;
      }).at(-1);
      setCurrent(active?.id ?? sections[0]?.id);
    }
    update();
    const observer = new ResizeObserver(update);
    observer.observe(editor.view.dom);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [editor, sections]);

  if (!sections.length) return null;
  return <nav className="section-nav" aria-label="Article sections">
    {sections.map(({ id, label, position }) => <a href={`#${id}`} key={id} aria-label={label}
      title={label} aria-current={id === current ? "location" : undefined} onClick={(event) => {
        if (!editor?.isEditable || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        editor.chain().focus().setTextSelection(position + 1).scrollIntoView().run();
      }}><span>{label}</span></a>)}
  </nav>;
}
