import { Alert, Grid, Stack, Title } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import MailTemplateEditor from "../components/mail/MailTemplateEditor";
import MailTemplateList from "../components/mail/MailTemplateList";
import { useWarnOnLeave } from "../hooks/use-warn-on-leave";
import { useListMailTemplates } from "../orval/generated/mail/mail";

const MailTemplates = () => {
  const { t } = useTranslation();
  const { data: templates, isLoading, isError } = useListMailTemplates();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  const activeKey = selectedKey ?? templates?.[0]?.key ?? null;

  useWarnOnLeave(isDirty);

  const selectTemplate = (key: string) => {
    if (key === activeKey) return;
    if (isDirty && !window.confirm(t("mail_templates.discard_confirm"))) {
      return;
    }
    setIsDirty(false);
    setSelectedKey(key);
  };

  return (
    <Stack gap="md">
      <BackButton to="/" />

      <Title order={2}>{t("mail_templates.title")}</Title>

      {isError ? <ErrorAlert>{t("mail_templates.error")}</ErrorAlert> : null}

      {isLoading ? <PageLoader /> : null}

      {templates && templates.length > 0 ? (
        <Grid gap="md" align="flex-start">
          <Grid.Col span={{ base: 12, md: 4, lg: 3 }}>
            <MailTemplateList
              templates={templates}
              activeKey={activeKey}
              onSelect={selectTemplate}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 8, lg: 9 }}>
            {activeKey ? (
              <MailTemplateEditor
                key={activeKey}
                templateKey={activeKey}
                onDirtyChange={setIsDirty}
              />
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
