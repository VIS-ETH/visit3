import { useState } from "react";
import { TextInput, Stack } from "@mantine/core";
import { IconMailSearch } from "@tabler/icons-react";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { passwordResetRequestSchema } from "../schemas/passwordResetRequestSchema";
import { useTranslation } from "react-i18next";
import { useRequestPasswordReset } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import { useAsyncAction } from "../hooks/use-async-action";
import { notifySuccess } from "../utils/notify";

const RequestPasswordReset = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("password_reset_request.title"));
  const [sentTo, setSentTo] = useState<string | null>(null);

  const { mutateAsync: requestPasswordReset } = useRequestPasswordReset();

  const { run: sendResetMail, isRunning } = useAsyncAction(
    async (email: string) => {
      await requestPasswordReset({ data: { email } });
      setSentTo(email);
      notifySuccess(t("password_reset_request.sent"));
    },
  );

  const form = useTranslatedForm<typeof passwordResetRequestSchema>(
    passwordResetRequestSchema,
    {
      initialValues: {
        email: "",
      },
    },
  );

  return (
    <AuthCardLayout
      title={t("password_reset_request.title")}
      maxWidth={620}
      backTo="/login"
    >
      <form
        onSubmit={form.onSubmit(
          (values) => void sendResetMail(values.email.trim()),
        )}
      >
        <Stack gap="md">
          <TextInput
            label={t("email.title")}
            placeholder={t("register.email.placeholder")}
            autoComplete="email"
            size="md"
            leftSection={<IconMailSearch size={16} />}
            {...form.getInputProps("email")}
          />
          <AuthButton
            type="submit"
            loading={isRunning}
            disabled={isRunning || form.values.email.trim() === sentTo}
          >
            {t("password_reset_request.submit")}
          </AuthButton>
        </Stack>
      </form>
    </AuthCardLayout>
  );
};

export default RequestPasswordReset;
