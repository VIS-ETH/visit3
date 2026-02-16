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
import { IconLock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import { resetPasswordSchema } from "../schemas/resetPasswordSchema";
import BackButton from "../components/BackButton";
import { useState } from "react";
import {
  useResetPassword,
  useValidResetPassword,
} from "../orval/generated/auth/auth";

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

  if (token === undefined) {
    navigate("/login");
    return;
  }

  if (validPending) {
    return <LoadingOverlay />;
  }

  if (passwordReset || validError || !valid) {
    return (
      <>
        <BackButton to="/login" />
        <Center py="xl">
          <Stack align="center" gap="xl" maw={400} px="md">
            <Title order={2} ta="center">
              {passwordReset
                ? t("reset_password.done")
                : t("reset_password.invalid")}
            </Title>
            <Button component="a" href="/login" variant="light">
              Back to Login
            </Button>
          </Stack>
        </Center>
      </>
    );
  }

  return (
    <>
      <BackButton to="/login" />
      <Center py="xl">
        <Stack align="center" gap="xl" maw={400} px="md">
          <Stack gap="xs" align="center">
            <Title ta="center">{t("reset_password.title")}</Title>
          </Stack>

          <Paper w="100%" p="xl" radius="md" withBorder>
            <form
              onSubmit={form.onSubmit((values) => {
                reset({
                  data: { token: token, new_password: values.password },
                });
              })}
            >
              <Stack gap="md">
                {resetError && (
                  <Alert color="red" title={t("forget_password.fail")}>
                    {t("reset_password.error")}
                  </Alert>
                )}
                <PasswordInput
                  label={t("register.password.title")}
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("password")}
                />
                <PasswordInput
                  label={t("register.password.confirm")}
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("confirmPassword")}
                />
                <Button
                  type="submit"
                  loading={resetPending}
                  disabled={resetPending}
                  size="md"
                >
                  {t("reset_password.submit")}
                </Button>
              </Stack>
            </form>
          </Paper>
        </Stack>
      </Center>
    </>
  );
}
