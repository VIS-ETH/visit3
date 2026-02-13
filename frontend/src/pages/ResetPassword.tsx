import { useNavigate, useParams } from "react-router";
import {
  Alert,
  Button,
  Center,
  LoadingOverlay,
  Paper,
  PasswordInput,
  Stack,
  Title,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import { resetPasswordSchema } from "../schemas/resetPasswordSchema";
import BackButton from "../components/BackButton";
import { useState } from "react";
import { useResetPassword, useValidResetPassword } from "../orval/generated/auth/auth";

export default function ResetPassword() {
  const { token } = useParams();
  const { t } = useTranslation();
  const [passwordReset, setPasswordReset] = useState(false);
  const navigate = useNavigate();

  if (token === undefined) {
    navigate("/login");
    return;
  }

  const {
    data: valid,
    isPending:validPending,
    isError: validError,
  } = useValidResetPassword(token, {
    query: {
      retry: false,
    },
  });

  const {
    mutate: reset,
    isPending: resetPending,
    isError: resetError,
  } = useResetPassword({
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
    },
  );

  if (validPending) {return (<LoadingOverlay />)};

  if (passwordReset || validError || !valid) {
    return (
      <>
        <BackButton to="/login" />
        <Center>
          <Title order={3}>
            {passwordReset
              ? t("reset_password.done")
              : t("reset_password.invalid")}
          </Title>
        </Center>
      </>
    );
  }

  return (
    <>
      <BackButton to="/login" />
      <Center mb="md">
        <Title>{t("reset_password.title")}</Title>
      </Center>
      <form
        onSubmit={form.onSubmit((values) => {
          reset({
            data: {token: token, new_password: values.password}
          });
        })}
      >
        <Center>
          <Paper w="100%" maw={380} p="xl" radius="md" withBorder>
            <Stack>
              {resetError && (
                <Alert color="red" title={t("forget_password.fail")}>
                  {t("reset_password.error")}
                </Alert>
              )}
              <PasswordInput
                label={t("register.password.title")}
                autoComplete="new-password"
                placeholder="************"
                {...form.getInputProps("password")}
              />
              <PasswordInput
                label={t("register.password.confirm")}
                autoComplete="new-password"
                placeholder="************"
                {...form.getInputProps("confirmPassword")}
              />
              <Button type="submit" loading={resetPending} disabled={resetPending}>
                {t("reset_password.submit")}
              </Button>
            </Stack>
          </Paper>
        </Center>
      </form>
    </>
  );
}
