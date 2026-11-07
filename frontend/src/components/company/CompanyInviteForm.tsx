import {
  Alert,
  Button,
  Group,
  Paper,
  Stack,
  TextInput,
  Title,
} from "@mantine/core";
import { IconMail } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../hooks/use-async-action";
import { createCompanyInvite } from "../../orval/generated/company/company";
import { inviteSchema } from "../../schemas/inviteSchema";
import { notifySuccess } from "../../utils/notify";
import { useTranslatedForm } from "../../utils/translator";

const CompanyInviteForm = ({ confirmed }: { confirmed?: boolean }) => {
  const { t } = useTranslation();
  const form = useTranslatedForm<typeof inviteSchema>(inviteSchema, {
    initialValues: { email: "" },
  });

  const canInvite = confirmed === true;
  const { run: sendInvite, isRunning: isSending } = useAsyncAction(
    async (email: string) => {
      await createCompanyInvite({ email });
      if (form.getValues().email.trim() === email) form.reset();
      notifySuccess(t("company_profile.invite_success", { email }));
    },
  );

  return (
    <Paper withBorder p="xl" radius="md">
      <Stack gap="md">
        <Title order={4}>
          <IconMail
            size={18}
            style={{ marginRight: 6, verticalAlign: "middle" }}
          />
          {t("company_profile.invite_title")}
        </Title>
        {confirmed === false ? (
          <Alert color="blue" variant="light">
            {t("company_profile.invite_unconfirmed")}
          </Alert>
        ) : null}
        <form onSubmit={form.onSubmit((v) => void sendInvite(v.email.trim()))}>
          <Group align="flex-end" gap="sm">
            <TextInput
              style={{ flex: 1 }}
              label={t("company_profile.invite_email")}
              placeholder={t("company_profile.invite_email_placeholder")}
              disabled={!canInvite}
              {...form.getInputProps("email")}
            />
            <Button
              type="submit"
              loading={isSending}
              disabled={!canInvite || !form.isValid()}
            >
              {t("company_profile.invite_button")}
            </Button>
          </Group>
        </form>
      </Stack>
    </Paper>
  );
};

export default CompanyInviteForm;
