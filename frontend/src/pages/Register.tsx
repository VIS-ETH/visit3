import { useState } from "react";
import {
  Alert,
  Button,
  TextInput,
  PasswordInput,
  Stack,
  Center,
  Paper,
  Title,
} from "@mantine/core";
import type { AxiosError } from "axios";
import { useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { registerSchema } from "../schemas/registerSchema";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import BackButton from "../components/BackButton";
import { useRegisterUser } from "../orval/generated/auth/auth";

const Register = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("register.title"));
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const { mutate: register, isPending } = useRegisterUser({
    mutation: {
      onSuccess: () => {
        navigate("/login");
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

  const form = useTranslatedForm<typeof registerSchema>(registerSchema, {
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  return (
    <>
      <BackButton to="/login" />
      <form
        onSubmit={form.onSubmit((values) => {
          setError("");
          register({
            data: { email: values.email, password: values.password },
          });
        })}
      >
        <Center mb="md">
          <Title>{t("register.title")}</Title>
        </Center>
        <Center>
          <Paper w="100%" maw={380} p="xl" radius="md" withBorder>
            <Stack>
              {error && (
                <Alert color="red" title={t("register.fail")}>
                  {t(error)}
                </Alert>
              )}
              <TextInput
                label={t("email.title")}
                autoComplete="email"
                placeholder={t("register.email.placeholder")}
                {...form.getInputProps("email")}
              />
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
              <Button type="submit" loading={isPending} disabled={isPending}>
                {t("register.button")}
              </Button>
            </Stack>
          </Paper>
        </Center>
      </form>
    </>
  );
};

export default Register;
