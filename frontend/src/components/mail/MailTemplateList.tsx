import { Badge, Button, Paper, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { MailTemplateResponse } from "../../orval/generated/fastAPI.schemas";

const formatUpdatedAt = (value?: string | null) => {
  if (!value) return null;
  const updatedAt = new Date(value);
  if (Number.isNaN(updatedAt.getTime())) return null;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    updatedAt,
  );
};

interface MailTemplateListProps {
  templates: MailTemplateResponse[];
  activeKey: string | null;
  onSelect: (key: string) => void;
}

const MailTemplateList = ({
  templates,
  activeKey,
  onSelect,
}: MailTemplateListProps) => {
  const { t } = useTranslation();

  return (
    <Paper withBorder p="md" radius="md">
      <Stack gap="xs">
        <Title order={4}>{t("mail_templates.list_title")}</Title>
        {templates.map((template) => {
          const updatedAt = formatUpdatedAt(template.updated_at);
          return (
            <Button
              key={template.key}
              variant={template.key === activeKey ? "light" : "subtle"}
              justify="space-between"
              h="auto"
              py="xs"
              onClick={() => onSelect(template.key)}
              rightSection={
                template.is_customized ? (
                  <Badge size="xs" variant="light">
                    {t("mail_templates.customized")}
                  </Badge>
                ) : null
              }
            >
              <Stack gap={0} align="flex-start">
                <Text size="sm">{template.key}</Text>
                <Text size="xs" c="dimmed">
                  {updatedAt ?? t("mail_templates.never_updated")}
                </Text>
              </Stack>
            </Button>
          );
        })}
      </Stack>
    </Paper>
  );
};
export default MailTemplateList;
