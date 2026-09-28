import { Button, Code, Collapse, Grid, Stack, Text } from "@mantine/core";
import { IconChevronDown, IconChevronUp } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { MailTemplateResponse } from "../../orval/generated/fastAPI.schemas";
import {
  mailTemplateDefaults,
  mailTemplateFields,
  type MailTemplateLanguage,
} from "../../utils/mail-template";
import type { MailTemplateFormValues } from "../../schemas/mailTemplateSchema";

interface MailTemplateDefaultsProps {
  template: MailTemplateResponse;
  values: MailTemplateFormValues;
  language: MailTemplateLanguage;
}

const TextColumn = ({
  title,
  subject,
  body,
}: {
  title: string;
  subject: string;
  body: string;
}) => {
  const { t } = useTranslation();

  return (
    <Stack gap={4}>
      <Text fw={600} size="sm">
        {title}
      </Text>
      <Text c="dimmed" size="xs">
        {t("mail_templates.subject")}
      </Text>
      <Code block>{subject}</Code>
      <Text c="dimmed" size="xs">
        {t("mail_templates.body")}
      </Text>
      <Code block>{body}</Code>
    </Stack>
  );
};

const MailTemplateDefaults = ({
  template,
  values,
  language,
}: MailTemplateDefaultsProps) => {
  const { t } = useTranslation();
  const [opened, setOpened] = useState(false);
  const fields = mailTemplateFields(language);
  const defaults = mailTemplateDefaults(template, language);

  return (
    <Stack gap="xs">
      <Button
        variant="subtle"
        justify="space-between"
        rightSection={
          opened ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />
        }
        onClick={() => setOpened((current) => !current)}
      >
        {opened
          ? t("mail_templates.defaults_hide")
          : t("mail_templates.defaults_show")}
      </Button>
      <Collapse expanded={opened} keepMounted={false}>
        <Grid gap="md">
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextColumn
              title={t("mail_templates.defaults_current")}
              subject={values[fields.subject]}
              body={values[fields.body]}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextColumn
              title={t("mail_templates.defaults_default")}
              subject={defaults.subject}
              body={defaults.body}
            />
          </Grid.Col>
        </Grid>
      </Collapse>
    </Stack>
  );
};
export default MailTemplateDefaults;
