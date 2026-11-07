import { Badge, Button, Paper, Stack, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { MailTemplateResponse } from "../../orval/generated/fastAPI.schemas";

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
        {templates.map((template) => (
          <Button
            key={template.key}
            variant={template.key === activeKey ? "light" : "subtle"}
            justify="space-between"
            h="auto"
            py="xs"
            onClick={() => onSelect(template.key)}
            rightSection={
              !template.is_valid ? (
                <Badge size="xs" variant="light" color="red">
                  {t("mail_templates.invalid")}
                </Badge>
              ) : template.is_customized ? (
                <Badge size="xs" variant="light">
                  {t("mail_templates.customized")}
                </Badge>
              ) : null
            }
          >
            {template.key}
          </Button>
        ))}
      </Stack>
    </Paper>
  );
};
export default MailTemplateList;
