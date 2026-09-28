import { Input } from "@mantine/core";
import { RichTextEditor } from "@mantine/tiptap";
import { Bold } from "@tiptap/extension-bold";
import { Document } from "@tiptap/extension-document";
import { HardBreak } from "@tiptap/extension-hard-break";
import { Italic } from "@tiptap/extension-italic";
import { Paragraph } from "@tiptap/extension-paragraph";
import { Strike } from "@tiptap/extension-strike";
import { Text } from "@tiptap/extension-text";
import { Underline } from "@tiptap/extension-underline";
import { UndoRedo } from "@tiptap/extensions";
import { useEditor, type Editor } from "@tiptap/react";
import { memo, useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

const EXTENSIONS = [
  Document,
  Paragraph,
  Text,
  Bold,
  Italic,
  Underline,
  Strike,
  HardBreak,
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

const editorValue = (editor: Editor) =>
  editor.isEmpty ? "" : editor.getHTML();

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
      },
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
        }}
      >
        <RichTextEditor.Toolbar>
          <RichTextEditor.ControlsGroup>
            <RichTextEditor.Bold />
            <RichTextEditor.Italic />
            <RichTextEditor.Underline />
            <RichTextEditor.Strikethrough />
          </RichTextEditor.ControlsGroup>
        </RichTextEditor.Toolbar>
        <RichTextEditor.Content mih={120} />
      </RichTextEditor>
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
