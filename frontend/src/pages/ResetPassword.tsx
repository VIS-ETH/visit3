import { useNavigate, useParams } from "react-router";
import { LoadingOverlay, PasswordInput, Stack } from "@mantine/core";
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

export default function ResetPassword() {
  const { token } = useParams();
  const { t } = useTranslation();
  const [passwordReset, setPasswordReset] = useState(false);
  const navigate = useNavigate();

  const {
    data: valid,
    isPending: validPending,
    isError: validError,
  } = useValidResetPassword(token || "", {
    query: {
      retry: false,
      enabled: token !== undefined,
    },
  });

  const { mutate: reset, isPending: resetPending } = useResetPassword({
    mutation: {
      onSuccess: () => {
        setPasswordReset(true);
      },
    },
  });

  const form = useTranslatedForm<typeof resetPasswordSchema>(
    resetPasswordSchema,
    {
      initialValues: {
        password: "",
        confirmPassword: "",
      },
    }
  );

  if (token === undefined) {
    navigate("/login");
    return;
  }

  if (validPending) {
    return <LoadingOverlay />;
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
        onSubmit={form.onSubmit((values) => {
          reset({
            data: { token: token, new_password: values.password },
          });
        })}
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
}
