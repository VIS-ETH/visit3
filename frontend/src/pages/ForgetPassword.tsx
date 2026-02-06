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
import type { AxiosError } from "axios";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { forgetPasswordSchema } from "../schemas/forgetPasswordSchema";
import { useTranslation } from "react-i18next";
import { useForgetPassword } from "../orval/generated/users/users";
import BackButton from "../components/BackButton";

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
      <Center mb="md">
        <Title>{t("forget_password.title")}</Title>
      </Center>
      <form
        onSubmit={form.onSubmit((values) => {
          setError("");
          forgotPassword({
            data: { email: values.email },
          });
        })}
      >
        <Center>
          <Paper w="100%" maw={380} p="xl" radius="md" withBorder>
            <Stack>
              {emailSent && <Alert>{t("forget_password.sent")}</Alert>}
              {error && (
                <Alert color="red" title={t("forget_password.fail")}>
                  {t(error)}
                </Alert>
              )}
              <TextInput
                label={t("email.title")}
                placeholder="your@email.com"
                autoComplete="email"
                {...form.getInputProps("email")}
              />
              <Button
                type="submit"
                loading={isPending}
                disabled={isPending || emailSent}
              >
                {t("forget_password.submit")}
              </Button>
            </Stack>
          </Paper>
        </Center>
      </form>
    </>
  );
};

export default ForgetPassword;
