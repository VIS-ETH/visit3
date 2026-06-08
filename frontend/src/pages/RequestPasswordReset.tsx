import { useState } from "react";
import { TextInput, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMailSearch } from "@tabler/icons-react";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { passwordResetRequestSchema } from "../schemas/passwordResetRequestSchema";
import { useTranslation } from "react-i18next";
import { useRequestPasswordReset } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";

const RequestPasswordReset = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("password_reset_request.title"));
  const [emailSent, setEmailSent] = useState(false);

  const { mutate: requestPasswordReset, isPending } = useRequestPasswordReset({
    mutation: {
      onSuccess: () => {
        setEmailSent(true);
        notifications.show({
          color: "green",
          title: t("password_reset_request.title"),
          message: t("password_reset_request.sent"),
          autoClose: 4000,
        });
      },
    },
  });

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
      subtitle={t("welcome")}
      maxWidth={620}
      backTo="/login"
    >
      <form
        onSubmit={form.onSubmit((values) => {
          requestPasswordReset({
            data: { email: values.email },
          });
        })}
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
            loading={isPending}
            disabled={isPending || emailSent}
          >
            {t("password_reset_request.submit")}
          </AuthButton>
        </Stack>
      </form>
    </AuthCardLayout>
  );
};

export default RequestPasswordReset;
