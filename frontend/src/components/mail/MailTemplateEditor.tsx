import {
  Badge,
  Button,
  Divider,
  Group,
  Paper,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  IconArrowBackUp,
  IconMailForward,
  IconRefresh,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FocusEvent,
} from "react";
import { useTranslation } from "react-i18next";
import type {
  MailPreviewResponse,
  MailTemplateResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getGetMailTemplateQueryKey,
  getListMailTemplatesQueryKey,
  useGetMailTemplate,
  usePreviewMailTemplate,
  useResetMailTemplate,
  useTestSendMailTemplate,
  useUpdateMailTemplate,
} from "../../orval/generated/mail/mail";
import {
  emptyMailTemplateValues,
  mailTemplateSchema,
  toMailTemplateRequest,
  type MailTemplateFormValues,
} from "../../schemas/mailTemplateSchema";
import {
  getInvalidMailTemplateField,
  insertIntoSelection,
  mailTemplateFields,
  mailTemplateLanguageOf,
  mailTemplateValues,
  mailVariableSnippet,
  MAIL_TEMPLATE_LANGUAGES,
  type MailTemplateField,
  type MailTemplateLanguage,
} from "../../utils/mail-template";
import { notifySuccess } from "../../utils/notify";
import { useTranslatedForm } from "../../utils/translator";
import { useAsyncAction } from "../../hooks/use-async-action";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";
import MailTemplateDefaults from "./MailTemplateDefaults";
import MailTemplatePreview from "./MailTemplatePreview";
import MailTemplateResetModal from "./MailTemplateResetModal";

const BODY_ROWS = 16;

type FieldElement = HTMLInputElement | HTMLTextAreaElement;

interface MailTemplateEditorProps {
  templateKey: string;
  onDirtyChange?: (dirty: boolean) => void;
}

const MailTemplateEditor = ({
  templateKey,
  onDirtyChange,
}: MailTemplateEditorProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: template, isError } = useGetMailTemplate(templateKey);
  const [language, setLanguage] = useState<MailTemplateLanguage>("de");
  const [focusedField, setFocusedField] = useState<MailTemplateField>("bodyDe");
  const [preview, setPreview] = useState<MailPreviewResponse | null>(null);
  const [resetOpened, setResetOpened] = useState(false);
  const fieldElements = useRef<
    Partial<Record<MailTemplateField, FieldElement>>
  >({});
  const loadedKeyRef = useRef<string | null>(null);

  const form = useTranslatedForm<typeof mailTemplateSchema>(
    mailTemplateSchema,
    {
      initialValues: emptyMailTemplateValues,
    },
  );

  const { mutate: requestPreview, isPending: isPreviewing } =
    usePreviewMailTemplate({
      mutation: { onSuccess: setPreview },
    });

  const applyTemplate = useCallback(
    (loaded: MailTemplateResponse) => {
      loadedKeyRef.current = loaded.key;
      const values = mailTemplateValues(loaded);
      form.setInitialValues(values);
      form.setValues(values);
      form.resetDirty();
      form.clearErrors();
      requestPreview({ key: loaded.key });
    },
    [form, requestPreview],
  );

  useEffect(() => {
    if (!template || loadedKeyRef.current === template.key) return;
    applyTemplate(template);
  }, [template, applyTemplate]);

  const isDirty = form.isDirty();
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  const refreshTemplate = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: getListMailTemplatesQueryKey(),
      }),
      queryClient.invalidateQueries({
        queryKey: getGetMailTemplateQueryKey(templateKey),
      }),
    ]);

  const showInvalidField = (error: unknown) => {
    const invalid = getInvalidMailTemplateField(error);
    if (!invalid) return;
    setLanguage(mailTemplateLanguageOf(invalid.field));
    form.setFieldError(
      invalid.field,
      invalid.variable
        ? t("mail_templates.invalid_variable", { variable: invalid.variable })
        : t("mail_templates.invalid_field"),
    );
  };

  const { mutateAsync: updateTemplate } = useUpdateMailTemplate();
  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (values: MailTemplateFormValues) => {
      const saved = await updateTemplate({
        key: templateKey,
        data: toMailTemplateRequest(values),
      });
      await refreshTemplate();
      form.setInitialValues(values);
      form.resetDirty(values);
      notifySuccess(t("mail_templates.save_success"));
      requestPreview({ key: saved.key });
    },
    showInvalidField,
  );

  const { mutateAsync: resetTemplate } = useResetMailTemplate();
  const { run: reset, isRunning: isResetting } = useAsyncAction(async () => {
    const data = await resetTemplate({ key: templateKey });
    await refreshTemplate();
    applyTemplate(data);
    setResetOpened(false);
    notifySuccess(t("mail_templates.reset_success"));
  });

  const { mutate: testSend, isPending: isSending } = useTestSendMailTemplate({
    mutation: {
      onSuccess: () => {
        notifySuccess(t("mail_templates.test_send_success"));
      },
    },
  });

  const fieldProps = (field: MailTemplateField) => {
    const inputProps = form.getInputProps(field);
    return {
      ...inputProps,
      ref: (element: FieldElement | null) => {
        if (element) fieldElements.current[field] = element;
      },
      onFocus: (event: FocusEvent<FieldElement>) => {
        inputProps.onFocus?.(event);
        setFocusedField(field);
      },
    };
  };

  const insertVariable = (variable: string) => {
    const field = focusedField;
    const element = fieldElements.current[field];
    const value = form.getValues()[field];
    const start = element?.selectionStart ?? value.length;
    const end = element?.selectionEnd ?? value.length;
    const snippet = mailVariableSnippet(variable);
    form.setFieldValue(field, insertIntoSelection(value, snippet, start, end));

    const caret = start + snippet.length;
    window.setTimeout(() => {
      const target = fieldElements.current[field];
      if (!target) return;
      target.focus();
      target.setSelectionRange(caret, caret);
    }, 0);
  };

  const handleLanguageChange = (value: string | null) => {
    const next = MAIL_TEMPLATE_LANGUAGES.find(
      (candidate) => candidate === value,
    );
    if (!next) return;
    setLanguage(next);
    setFocusedField(mailTemplateFields(next).body);
  };

  if (isError) return <ErrorAlert />;
  if (!template) {
    return (
      <Paper withBorder p="lg" radius="md">
        <PageLoader />
      </Paper>
    );
  }

  return (
    <Paper withBorder p="lg" radius="md">
      <form onSubmit={form.onSubmit((values) => void save(values))}>
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Title order={4}>{template.key}</Title>
            {!template.is_valid ? (
              <Badge variant="light" color="red">
                {t("mail_templates.invalid")}
              </Badge>
            ) : template.is_customized ? (
              <Badge variant="light">{t("mail_templates.customized")}</Badge>
            ) : (
              <Badge variant="light" color="gray">
                {t("mail_templates.default")}
              </Badge>
            )}
          </Group>

          <Tabs
            value={language}
            onChange={handleLanguageChange}
            keepMounted={false}
          >
            <Tabs.List>
              <Tabs.Tab value="de">{t("mail_templates.tab_de")}</Tabs.Tab>
              <Tabs.Tab value="en">{t("mail_templates.tab_en")}</Tabs.Tab>
            </Tabs.List>
            {MAIL_TEMPLATE_LANGUAGES.map((value) => {
              const fields = mailTemplateFields(value);
              return (
                <Tabs.Panel key={value} value={value} pt="md">
                  <Stack gap="sm">
                    <TextInput
                      label={t("mail_templates.subject")}
                      disabled={isSaving}
                      {...fieldProps(fields.subject)}
                    />
                    <Textarea
                      label={t("mail_templates.body")}
                      autosize={false}
                      rows={BODY_ROWS}
                      disabled={isSaving}
                      styles={{
                        input: {
                          fontFamily: "var(--mantine-font-family-monospace)",
                        },
                      }}
                      {...fieldProps(fields.body)}
                    />
                  </Stack>
                </Tabs.Panel>
              );
            })}
          </Tabs>

          <div>
            <Text size="sm" fw={600}>
              {t("mail_templates.variables")}
            </Text>
            <Text c="dimmed" size="xs">
              {t("mail_templates.variables_hint")}
            </Text>
            <Group gap="xs" mt="xs">
              {template.variables.map((variable) => (
                <Button
                  key={variable}
                  size="compact-xs"
                  variant="light"
                  radius="xl"
                  disabled={isSaving}
                  onClick={() => insertVariable(variable)}
                >
                  {variable}
                </Button>
              ))}
            </Group>
          </div>

          <MailTemplateDefaults
            template={template}
            values={form.getValues()}
            language={language}
          />

          <Group justify="flex-end">
            {template.is_customized ? (
              <Button
                variant="default"
                color="red"
                leftSection={<IconArrowBackUp size={16} />}
                onClick={() => setResetOpened(true)}
              >
                {t("mail_templates.reset")}
              </Button>
            ) : null}
            <Button
              variant="default"
              leftSection={<IconMailForward size={16} />}
              loading={isSending}
              disabled={isDirty || isSaving}
              onClick={() => testSend({ key: templateKey })}
            >
              {t("mail_templates.test_send")}
            </Button>
            <Button type="submit" loading={isSaving}>
              {t("mail_templates.save")}
            </Button>
          </Group>
          {isDirty ? (
            <Text c="dimmed" size="xs" ta="right">
              {t("mail_templates.test_send_save_first")}
            </Text>
          ) : null}

          <Divider />

          <Group justify="space-between" align="center">
            <Title order={5}>{t("mail_templates.preview_title")}</Title>
            <Button
              variant="default"
              leftSection={<IconRefresh size={16} />}
              loading={isPreviewing}
              onClick={() => requestPreview({ key: templateKey })}
            >
              {t("mail_templates.preview_refresh")}
            </Button>
          </Group>
          <Text c="dimmed" size="xs">
            {t("mail_templates.preview_hint")}
          </Text>
          <MailTemplatePreview preview={preview} />
        </Stack>
      </form>
      <MailTemplateResetModal
        opened={resetOpened}
        templateKey={templateKey}
        isPending={isResetting}
        onConfirm={() => void reset()}
        onClose={() => setResetOpened(false)}
      />
    </Paper>
  );
};
export default MailTemplateEditor;
