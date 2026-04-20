import { useState } from "react";
import { Button, TextInput, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMailSearch } from "@tabler/icons-react";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { forgetPasswordSchema } from "../schemas/forgetPasswordSchema";
import { useTranslation } from "react-i18next";
import { useForgetPassword } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";

const ForgetPassword = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("forget_password.title"));
  const [emailSent, setEmailSent] = useState(false);

  const { mutate: forgotPassword, isPending } = useForgetPassword({
    mutation: {
      onSuccess: () => {
        setEmailSent(true);
        notifications.show({
          color: "green",
          title: t("forget_password.title"),
          message: t("forget_password.sent"),
          autoClose: 4000,
        });
      },
    },
  });

  const form = useTranslatedForm<typeof forgetPasswordSchema>(
    forgetPasswordSchema,
    {
      initialValues: {
        email: "",
      },
    }
  );

  return (
    <AuthCardLayout
      title={t("forget_password.title")}
      subtitle={t("welcome")}
      maxWidth={620}
      backTo="/login"
    >
      <form
        className="login-form"
        onSubmit={form.onSubmit((values) => {
          forgotPassword({
            data: { email: values.email },
          });
        })}
      >
        <Stack gap="md">
          <TextInput
            label={t("email.title")}
            placeholder="your@email.com"
            autoComplete="email"
            size="md"
            leftSection={<IconMailSearch size={16} />}
            {...form.getInputProps("email")}
          />
          <Button
            type="submit"
            loading={isPending}
            disabled={isPending || emailSent}
            size="md"
            fullWidth
            className="login-primary-button login-uniform-control"
          >
            {t("forget_password.submit")}
          </Button>
        </Stack>
      </form>
    </AuthCardLayout>
  );
};

export default ForgetPassword;
