import {
  Button,
  Group,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconAlertCircle } from "@tabler/icons-react";
import { useRef, useState, type FocusEvent } from "react";
import { useTranslation } from "react-i18next";
import type { MailCampaignFormValues } from "../../schemas/mailCampaignSchema";
import {
  insertIntoSelection,
  mailTemplateFields,
  mailVariableSnippet,
  MAIL_TEMPLATE_LANGUAGES,
  type MailTemplateField,
  type MailTemplateLanguage,
} from "../../utils/mail-template";

const BODY_ROWS = 12;

type FieldElement = HTMLInputElement | HTMLTextAreaElement;

interface MailCampaignContentProps {
  form: UseFormReturnType<MailCampaignFormValues>;
  variables: string[];
  disabled: boolean;
}

const MailCampaignContent = ({
  form,
  variables,
  disabled,
}: MailCampaignContentProps) => {
  const { t } = useTranslation();
  const [language, setLanguage] = useState<MailTemplateLanguage>("de");
  const [focusedField, setFocusedField] = useState<MailTemplateField>("bodyDe");
  const fieldElements = useRef<
    Partial<Record<MailTemplateField, FieldElement>>
  >({});

  const hasErrors = (tab: MailTemplateLanguage) => {
    const fields = mailTemplateFields(tab);
    return (
      Boolean(form.errors[fields.subject]) || Boolean(form.errors[fields.body])
    );
  };
  const errorMark = (tab: MailTemplateLanguage) =>
    hasErrors(tab) ? (
      <IconAlertCircle size={14} color="var(--mantine-color-red-6)" />
    ) : null;

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

  return (
    <Stack gap="sm">
      <Tabs
        value={language}
        onChange={handleLanguageChange}
        keepMounted={false}
      >
        <Tabs.List>
          <Tabs.Tab value="de" rightSection={errorMark("de")}>
            {t("mail_templates.tab_de")}
          </Tabs.Tab>
          <Tabs.Tab value="en" rightSection={errorMark("en")}>
            {t("mail_campaigns.tab_en_optional")}
          </Tabs.Tab>
        </Tabs.List>
        {MAIL_TEMPLATE_LANGUAGES.map((value) => {
          const fields = mailTemplateFields(value);
          return (
            <Tabs.Panel key={value} value={value} pt="md">
              <Stack gap="sm">
                {value === "en" ? (
                  <Text c="dimmed" size="xs">
                    {t("mail_campaigns.english_hint")}
                  </Text>
                ) : null}
                <TextInput
                  label={t("mail_templates.subject")}
                  disabled={disabled}
                  {...fieldProps(fields.subject)}
                />
                <Textarea
                  label={t("mail_templates.body")}
                  autosize={false}
                  rows={BODY_ROWS}
                  disabled={disabled}
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
          {variables.map((variable) => (
            <Tooltip
              key={variable}
              label={t(`mail_campaigns.variable.${variable}`)}
              withArrow
            >
              <Button
                size="compact-xs"
                variant="light"
                radius="xl"
                disabled={disabled}
                onClick={() => insertVariable(variable)}
              >
                {variable}
              </Button>
            </Tooltip>
          ))}
        </Group>
      </div>
    </Stack>
  );
};
export default MailCampaignContent;
