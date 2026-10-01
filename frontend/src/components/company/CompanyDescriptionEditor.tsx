import { Input, Text } from "@mantine/core";
import { RichTextEditor, useRichTextEditorContext } from "@mantine/tiptap";
import { IconIndentDecrease, IconIndentIncrease } from "@tabler/icons-react";
import { Bold } from "@tiptap/extension-bold";
import { Document } from "@tiptap/extension-document";
import { HardBreak } from "@tiptap/extension-hard-break";
import { Italic } from "@tiptap/extension-italic";
import { ListItem } from "@tiptap/extension-list";
import { Paragraph } from "@tiptap/extension-paragraph";
import { Strike } from "@tiptap/extension-strike";
import { Text as TextNode } from "@tiptap/extension-text";
import { Underline } from "@tiptap/extension-underline";
import { UndoRedo } from "@tiptap/extensions";
import { DOMParser as ProseMirrorParser } from "@tiptap/pm/model";
import { useEditor, useEditorState, type Editor } from "@tiptap/react";
import {
  memo,
  useEffect,
  useRef,
  type ComponentType,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import {
  cleanPastedHtml,
  plainTextToDom,
} from "../../utils/pasted-description";
import {
  canIndent,
  canOutdent,
  DESCRIPTION_LIST_EXTENSIONS,
} from "./description-extensions";

const EXTENSIONS = [
  Document,
  Paragraph,
  TextNode,
  Bold,
  Italic,
  Underline,
  Strike,
  HardBreak,
  ...DESCRIPTION_LIST_EXTENSIONS,
  UndoRedo,
];

interface CompanyDescriptionEditorProps {
  id: string;
  label: string;
  description: ReactNode;
  value: string;
  error?: ReactNode;
  disabled: boolean;
  onChange: (value: string) => void;
}

interface ListLevelControlProps {
  label: string;
  icon: ComponentType<{ className?: string; style?: object }>;
  enabled: (editor: Editor) => boolean;
  run: (editor: Editor) => void;
}

const editorValue = (editor: Editor) =>
  editor.isEmpty ? "" : editor.getHTML();

const ListLevelControl = ({
  label,
  icon: Icon,
  enabled,
  run,
}: ListLevelControlProps) => {
  const { editor, getStyles } = useRichTextEditorContext();
  const disabled = useEditorState({
    editor,
    selector: ({ editor: current }) =>
      !current || current.isDestroyed || !enabled(current),
  });
  return (
    <RichTextEditor.Control
      aria-label={label}
      title={label}
      disabled={disabled ?? true}
      onClick={() => {
        if (editor) run(editor);
      }}
    >
      <Icon {...getStyles("controlIcon")} />
    </RichTextEditor.Control>
  );
};

const CompanyDescriptionEditor = ({
  id,
  label,
  description,
  value,
  error,
  disabled,
  onChange,
}: CompanyDescriptionEditorProps) => {
  const { t } = useTranslation();
  const labelId = `${id}-label`;
  const hintId = `${id}-hint`;
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });
  const editor = useEditor({
    extensions: EXTENSIONS,
    content: value,
    editable: !disabled,
    editorProps: {
      attributes: {
        id,
        role: "textbox",
        "aria-multiline": "true",
        "aria-labelledby": labelId,
        "aria-describedby": hintId,
      },
      transformPastedHTML: cleanPastedHtml,
      clipboardTextParser: (text, context, _plain, view) =>
        ProseMirrorParser.fromSchema(view.state.schema).parseSlice(
          plainTextToDom(text),
          { preserveWhitespace: true, context },
        ),
    },
    onUpdate: ({ editor: updated }) => {
      onChangeRef.current(editorValue(updated));
    },
  });

  useEffect(() => {
    if (value !== editorValue(editor)) {
      editor.commands.setContent(value, { emitUpdate: false });
    }
  }, [editor, value]);

  useEffect(() => {
    editor.setEditable(!disabled);
  }, [editor, disabled]);

  return (
    <Input.Wrapper
      label={label}
      labelProps={{ id: labelId }}
      description={description}
      error={error}
      withAsterisk
    >
      <RichTextEditor
        editor={editor}
        labels={{
          boldControlLabel: t("company_profile_form.editor_bold"),
          italicControlLabel: t("company_profile_form.editor_italic"),
          underlineControlLabel: t("company_profile_form.editor_underline"),
          strikeControlLabel: t("company_profile_form.editor_strike"),
          bulletListControlLabel: t("company_profile_form.editor_bullet_list"),
          orderedListControlLabel: t(
            "company_profile_form.editor_ordered_list",
          ),
          undoControlLabel: t("company_profile_form.editor_undo"),
          redoControlLabel: t("company_profile_form.editor_redo"),
        }}
      >
        <RichTextEditor.Toolbar>
          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Bold />
            <RichTextEditor.Italic />
            <RichTextEditor.Underline />
            <RichTextEditor.Strikethrough />
          </RichTextEditor.ControlsGroup>
          <RichTextEditor.ControlsGroup>
            <RichTextEditor.BulletList />
            <RichTextEditor.OrderedList />
            <ListLevelControl
              label={t("company_profile_form.editor_indent")}
              icon={IconIndentIncrease}
              enabled={canIndent}
              run={(current) =>
                current.chain().focus().sinkListItem(ListItem.name).run()
              }
            />
            <ListLevelControl
              label={t("company_profile_form.editor_outdent")}
              icon={IconIndentDecrease}
              enabled={canOutdent}
              run={(current) =>
                current.chain().focus().liftListItem(ListItem.name).run()
              }
            />
          </RichTextEditor.ControlsGroup>
          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Undo />
            <RichTextEditor.Redo />
          </RichTextEditor.ControlsGroup>
        </RichTextEditor.Toolbar>
        <RichTextEditor.Content mih={120} />
      </RichTextEditor>
      <Text id={hintId} size="xs" c="dimmed" mt={4}>
        {t("company_profile_form.editor_hint")}
      </Text>
    </Input.Wrapper>
  );
};

const sameDisplay = (
  previous: CompanyDescriptionEditorProps,
  next: CompanyDescriptionEditorProps,
) =>
  previous.id === next.id &&
  previous.label === next.label &&
  previous.description === next.description &&
  previous.value === next.value &&
  previous.error === next.error &&
  previous.disabled === next.disabled;

export default memo(CompanyDescriptionEditor, sameDisplay);
