import { useState } from "react";
import {
  Alert,
  Button,
  TextInput,
  Stack,
  Center,
  Title,
  Paper,
} from "@mantine/core";
import { IconMailSearch } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { forgetPasswordSchema } from "../schemas/forgetPasswordSchema";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import { useForgetPassword } from "../orval/generated/auth/auth";

const ForgetPassword = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("forget_password.title"));
  const [error, setError] = useState("");

  const [emailSent, setEmailSent] = useState(false);

  const { mutate: forgotPassword, isPending } = useForgetPassword({
    mutation: {
      onSuccess: () => {
        setEmailSent(true);
      },
      onError: (e: AxiosError<{ detail?: any }>) => {
        const message =
          typeof e.response?.data?.detail === "string"
            ? e.response?.data?.detail
            : "server.error";

        setError(message);
      },
    },
  });

  const form = useTranslatedForm<typeof forgetPasswordSchema>(
    forgetPasswordSchema,
    {
      initialValues: {
        email: "",
      },
    },
  );

  return (
    <>
      <BackButton to="/login" />
      <Center py="xl">
        <Stack align="center" gap="xl" maw={400} px="md">
          <Stack gap="xs" align="center">
            <Title ta="center">{t("forget_password.title")}</Title>
          </Stack>

          <Paper w="100%" p="xl" radius="md" withBorder>
            <form
              onSubmit={form.onSubmit((values) => {
                setError("");
                forgotPassword({
                  data: { email: values.email },
                });
              })}
            >
              <Stack gap="md">
                {emailSent && (
                  <Alert color="green" title="Success">
                    {t("forget_password.sent")}
                  </Alert>
                )}
                {error && (
                  <Alert color="red" title={t("forget_password.fail")}>
                    {t(error)}
                  </Alert>
                )}
                <TextInput
                  label={t("email.title")}
                  placeholder="your@email.com"
                  autoComplete="email"
                  leftSection={<IconMailSearch size={16} />}
                  {...form.getInputProps("email")}
                />
                <Button
                  type="submit"
                  loading={isPending}
                  disabled={isPending || emailSent}
                  size="md"
                >
                  {t("forget_password.submit")}
                </Button>
              </Stack>
            </form>
          </Paper>
        </Stack>
      </Center>
    </>
  );
};

export default ForgetPassword;
