import { Extension, type Editor } from "@tiptap/core";
import {
  BulletList,
  ListItem,
  ListKeymap,
  OrderedList,
} from "@tiptap/extension-list";
import type { Node as ProseMirrorNode, ResolvedPos } from "@tiptap/pm/model";
import { Plugin, TextSelection, type Transaction } from "@tiptap/pm/state";

export const MAX_LIST_LEVEL = 2;
const MAX_LINE_BREAKS = 2;
const LIST_NAMES = new Set([BulletList.name, OrderedList.name]);
const BLANK_TEXT = /^\s*$/;

const listLevel = ($pos: ResolvedPos) => {
  let level = 0;
  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    if (LIST_NAMES.has($pos.node(depth).type.name)) level += 1;
  }
  return level;
};

export const canIndent = (editor: Editor) =>
  listLevel(editor.state.selection.$from) < MAX_LIST_LEVEL &&
  editor.can().sinkListItem(ListItem.name);

export const canOutdent = (editor: Editor) =>
  editor.can().liftListItem(ListItem.name);

const tooDeepList = (doc: ProseMirrorNode) => {
  let found: number | null = null;
  doc.descendants((node, pos) => {
    if (found !== null) return false;
    if (
      LIST_NAMES.has(node.type.name) &&
      listLevel(doc.resolve(pos)) >= MAX_LIST_LEVEL
    ) {
      found = pos;
      return false;
    }
    return true;
  });
  return found as number | null;
};

const flattenLists = (tr: Transaction) => {
  for (let pos = tooDeepList(tr.doc); pos !== null; pos = tooDeepList(tr.doc)) {
    const list = tr.doc.nodeAt(pos);
    if (!list) return;
    const target = tr.doc.resolve(pos).after() - list.nodeSize;
    const { from, to } = tr.selection;
    const inside = from > pos && to < pos + list.nodeSize;
    tr.delete(pos, pos + list.nodeSize).insert(target, list.content);
    if (inside) {
      const shift = target - pos - 1;
      tr.setSelection(TextSelection.create(tr.doc, from + shift, to + shift));
    }
  }
};

const removeExtraLineBreaks = (tr: Transaction) => {
  const extra: number[] = [];
  tr.doc.descendants((node, pos) => {
    if (!node.isTextblock) return true;
    let breaks = 0;
    node.forEach((child, offset) => {
      breaks = child.type.name === "hardBreak" ? breaks + 1 : 0;
      if (breaks > MAX_LINE_BREAKS) extra.push(pos + 1 + offset);
    });
    return false;
  });
  for (const at of extra.reverse()) tr.delete(at, at + 1);
};

const isBlankParagraph = (node: ProseMirrorNode) =>
  node.type.name === "paragraph" && BLANK_TEXT.test(node.textContent);

const removeExtraBlankLines = (tr: Transaction) => {
  const cursor = tr.selection.from;
  const extra: [number, number][] = [];
  let run: [number, number][] = [];
  const closeRun = () => {
    const away = run.filter(([from, to]) => cursor < from || cursor > to);
    extra.push(...away.slice(1));
    run = [];
  };
  tr.doc.forEach((node, offset) => {
    if (isBlankParagraph(node)) run.push([offset, offset + node.nodeSize]);
    else closeRun();
  });
  closeRun();
  for (const [from, to] of extra.reverse()) tr.delete(from, to);
};

export const DescriptionShape = Extension.create({
  name: "descriptionShape",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        appendTransaction: (transactions, _previous, state) => {
          if (!transactions.some((transaction) => transaction.docChanged)) {
            return null;
          }
          const tr = state.tr;
          flattenLists(tr);
          removeExtraLineBreaks(tr);
          removeExtraBlankLines(tr);
          return tr.docChanged ? tr : null;
        },
      }),
    ];
  },
});

export const DescriptionOrderedList = OrderedList.extend({
  addAttributes() {
    return {
      start: { default: 1, parseHTML: () => 1, renderHTML: () => ({}) },
      type: { default: null, parseHTML: () => null, renderHTML: () => ({}) },
    };
  },
});

export const DescriptionListItem = ListItem.extend({
  addKeyboardShortcuts() {
    return {
      ...this.parent?.(),
      Tab: () =>
        canIndent(this.editor) && this.editor.commands.sinkListItem(this.name),
    };
  },
});

export const DESCRIPTION_LIST_EXTENSIONS = [
  BulletList,
  DescriptionOrderedList,
  DescriptionListItem,
  ListKeymap,
  DescriptionShape,
];
