import { Navigate, useParams } from "react-router";
import { PasswordInput, Stack } from "@mantine/core";
import { IconLock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import { resetPasswordSchema } from "../schemas/resetPasswordSchema";
import { useState } from "react";
import {
  useResetPassword,
  useValidResetPassword,
} from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import PageLoader from "../components/PageLoader";
import { useAsyncAction } from "../hooks/use-async-action";

const ResetPassword = () => {
  const { token } = useParams();
  const { t } = useTranslation();
  const [passwordReset, setPasswordReset] = useState(false);

  const {
    data: valid,
    isPending: validPending,
    isError: validError,
  } = useValidResetPassword(token ?? "", {
    query: {
      retry: false,
      enabled: token !== undefined,
    },
  });

  const { mutateAsync: resetPassword } = useResetPassword();

  const { run: submitReset, isRunning: resetPending } = useAsyncAction(
    async (resetToken: string, newPassword: string) => {
      await resetPassword({
        data: { token: resetToken, new_password: newPassword },
      });
      setPasswordReset(true);
    },
  );

  const form = useTranslatedForm<typeof resetPasswordSchema>(
    resetPasswordSchema,
    {
      initialValues: {
        password: "",
        confirmPassword: "",
      },
    },
  );

  if (token === undefined) {
    return <Navigate to="/login" replace />;
  }

  if (validPending) {
    return <PageLoader />;
  }

  if (passwordReset || validError || !valid) {
    return (
      <AuthCardLayout
        title={
          passwordReset ? t("reset_password.done") : t("reset_password.invalid")
        }
        maxWidth={620}
        backTo="/login"
      >
        <AuthButton component="a" href="/login" intent="secondary">
          {t("email.confirm.back_to_login")}
        </AuthButton>
      </AuthCardLayout>
    );
  }

  return (
    <AuthCardLayout
      title={t("reset_password.title")}
      maxWidth={620}
      backTo="/login"
    >
      <form
        onSubmit={form.onSubmit(
          (values) => void submitReset(token, values.password),
        )}
      >
        <Stack gap="md">
          <PasswordInput
            label={t("register.password.title")}
            autoComplete="new-password"
            size="md"
            placeholder="************"
            leftSection={<IconLock size={16} />}
            {...form.getInputProps("password")}
          />
          <PasswordInput
            label={t("register.password.confirm")}
            autoComplete="new-password"
            size="md"
            placeholder="************"
            leftSection={<IconLock size={16} />}
            {...form.getInputProps("confirmPassword")}
          />
          <AuthButton
            type="submit"
            loading={resetPending}
            disabled={resetPending}
          >
            {t("reset_password.submit")}
          </AuthButton>
        </Stack>
      </form>
    </AuthCardLayout>
  );
};
export default ResetPassword;
