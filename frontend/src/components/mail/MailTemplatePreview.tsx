import { Code, Stack, Tabs, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { MailPreviewResponse } from "../../orval/generated/fastAPI.schemas";

const PREVIEW_FRAME_HEIGHT = 420;

const MailTemplatePreview = ({
  preview,
}: {
  preview: MailPreviewResponse | null;
}) => {
  const { t } = useTranslation();

  if (!preview) {
    return (
      <Text c="dimmed" size="sm">
        {t("mail_templates.preview_empty")}
      </Text>
    );
  }

  return (
    <Stack gap="xs">
      <Text size="sm" fw={600}>
        {preview.subject}
      </Text>
      <Tabs defaultValue="html">
        <Tabs.List>
          <Tabs.Tab value="html">{t("mail_templates.preview_html")}</Tabs.Tab>
          <Tabs.Tab value="text">{t("mail_templates.preview_text")}</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="html" pt="sm">
          <iframe
            title={t("mail_templates.preview_frame_title")}
            sandbox=""
            srcDoc={preview.html}
            width="100%"
            height={PREVIEW_FRAME_HEIGHT}
            style={{ border: 0 }}
          />
        </Tabs.Panel>
        <Tabs.Panel value="text" pt="sm">
          <Code block>{preview.text}</Code>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};
export default MailTemplatePreview;
