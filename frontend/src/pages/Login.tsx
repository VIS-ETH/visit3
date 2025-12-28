import { useState } from "react";
import {
  Alert,
  Button,
  TextInput,
  PasswordInput,
  Stack,
  Center,
  Title,
  Paper,
  Box,
} from "@mantine/core";
import type { AxiosError } from "axios";
import { NavLink, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useLoginUser } from "../orval/generated/users/users";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";

const Login = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("login.title"));
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: () => {
        navigate("/");
      },
      onError: (e: AxiosError<{ detail?: any }>) => {
        const message = e.response?.data?.detail
          ? JSON.stringify(e.response.data.detail)
          : "server.error";

        setError(message);
      },
    },
  });

  const form = useTranslatedForm<typeof loginSchema>(loginSchema, {
    initialValues: {
      username: "",
      password: "",
    },
  });

  return (
    <>
      <Center mb="md">
        <Title>{t("login.title")}</Title>
      </Center>
      <form
        onSubmit={form.onSubmit((values) => {
          setError("");
          login({
            data: { username: values.username, password: values.password },
          });
        })}
      >
        <Center>
          <Paper w="100%" maw={380} p="xl" radius="md" withBorder>
            <Stack>
              {error && (
                <Alert color="red" title="Login Failed">
                  {t(error)}
                </Alert>
              )}
              <TextInput
                label={t("register.email.title")}
                placeholder="your@email.com"
                autoComplete="email"
                {...form.getInputProps("username")}
              />
              <PasswordInput
                label={t("register.password.title")}
                placeholder="***********"
                autoComplete="password"
                {...form.getInputProps("password")}
              />
              <Button type="submit" loading={isPending} disabled={isPending}>
                {t("login.title")}
              </Button>
            </Stack>
          </Paper>
        </Center>
      </form>
      <Center mt="md">
        <Stack>
          <Button component={NavLink} to="/register">
            {t("login.register.title")}
          </Button>
        </Stack>
      </Center>
    </>
  );
};

export default Login;
