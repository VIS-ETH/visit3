import { Alert, Center, Grid, Loader, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import MailTemplateEditor from "../components/mail/MailTemplateEditor";
import MailTemplateList from "../components/mail/MailTemplateList";
import { useListMailTemplates } from "../orval/generated/mail/mail";

const MailTemplates = () => {
  const { t } = useTranslation();
  const { data: templates, isLoading, isError } = useListMailTemplates();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const activeKey = selectedKey ?? templates?.[0]?.key ?? null;

  return (
    <Stack gap="md">
      <BackButton to="/" />

      <div>
        <Title order={2}>{t("mail_templates.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("mail_templates.description")}
        </Text>
      </div>

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("mail_templates.error")}
        </Alert>
      ) : null}

      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : null}

      {templates && templates.length > 0 ? (
        <Grid gap="md" align="flex-start">
          <Grid.Col span={{ base: 12, md: 4, lg: 3 }}>
            <MailTemplateList
              templates={templates}
              activeKey={activeKey}
              onSelect={setSelectedKey}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 8, lg: 9 }}>
            {activeKey ? (
              <MailTemplateEditor key={activeKey} templateKey={activeKey} />
            ) : null}
          </Grid.Col>
        </Grid>
      ) : null}

      {templates?.length === 0 ? (
        <Alert
          icon={<IconAlertCircle />}
          color="blue"
          title={t("mail_templates.empty")}
        />
      ) : null}
    </Stack>
  );
};
export default MailTemplates;
