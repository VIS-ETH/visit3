import {
  Button,
  Group,
  Menu,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconAlertCircle, IconPlus } from "@tabler/icons-react";
import { Fragment, useRef, useState, type FocusEvent } from "react";
import { useTranslation } from "react-i18next";
import { useListServices } from "../../orval/generated/kp/kp";
import type { MailCampaignFormValues } from "../../schemas/mailCampaignSchema";
import {
  conditionalParagraph,
  serviceCondition,
} from "../../utils/mail-campaign";
import {
  insertIntoSelection,
  mailTemplateFields,
  mailVariableSnippet,
  MAIL_TEMPLATE_LANGUAGES,
  type MailTemplateField,
  type MailTemplateLanguage,
} from "../../utils/mail-template";
import {
  SERVICE_CATEGORY_LABEL_KEYS,
  servicesByCategory,
} from "../bookings/service-filter";

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
  const { eventId } = form.values;
  const { data: services } = useListServices(eventId, {
    query: { enabled: eventId.length > 0 },
  });
  const serviceGroups = servicesByCategory(services ?? []);

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

  const insert = (
    build: (selected: string) => { snippet: string; caret: number },
  ) => {
    const field = focusedField;
    const element = fieldElements.current[field];
    const value = form.getValues()[field];
    const start = element?.selectionStart ?? value.length;
    const end = element?.selectionEnd ?? value.length;
    const { snippet, caret: offset } = build(value.slice(start, end));
    form.setFieldValue(field, insertIntoSelection(value, snippet, start, end));
    const caret = start + offset;
    window.setTimeout(() => {
      const target = fieldElements.current[field];
      if (!target) return;
      target.focus();
      target.setSelectionRange(caret, caret);
    }, 0);
  };

  const insertVariable = (variable: string) =>
    insert(() => {
      const snippet = mailVariableSnippet(variable);
      return { snippet, caret: snippet.length };
    });

  const insertCondition = (condition: string) =>
    insert((selected) => conditionalParagraph(condition, selected));

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
          {serviceGroups.length > 0 ? (
            <Menu position="bottom-start" shadow="md" withinPortal>
              <Menu.Target>
                <Button
                  size="compact-xs"
                  variant="default"
                  radius="xl"
                  leftSection={<IconPlus size={12} />}
                  disabled={disabled}
                >
                  {t("mail_campaigns.condition.button")}
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                {serviceGroups.map((group) => (
                  <Fragment key={group.category}>
                    <Menu.Label>
                      {t(SERVICE_CATEGORY_LABEL_KEYS[group.category].group)}
                    </Menu.Label>
                    <Menu.Item
                      onClick={() =>
                        insertCondition(serviceCondition(group.category))
                      }
                    >
                      {t(SERVICE_CATEGORY_LABEL_KEYS[group.category].any)}
                    </Menu.Item>
                    {group.services.map((service) => (
                      <Menu.Item
                        key={service.id}
                        onClick={() =>
                          insertCondition(serviceCondition(service))
                        }
                      >
                        {service.name}
                      </Menu.Item>
                    ))}
                  </Fragment>
                ))}
              </Menu.Dropdown>
            </Menu>
          ) : null}
        </Group>
        {serviceGroups.length > 0 ? (
          <Text c="dimmed" size="xs" mt={6}>
            {t("mail_campaigns.condition.hint")}
          </Text>
        ) : null}
      </div>
    </Stack>
  );
};
export default MailCampaignContent;
