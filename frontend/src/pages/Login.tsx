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
  Text,
  Divider,
} from "@mantine/core";
import { IconLock, IconMailSearch } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { NavLink, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";
import { setToken } from "../api/utils";
import type { Token } from "../orval/generated/fastAPI.schemas";
import { useKeycloakInit, useLoginUser } from "../orval/generated/auth/auth";

const Login = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("login.title"));
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: (data: Token) => {
        setToken(data.access_token);
        navigate("/");
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

  const { refetch, isFetching } = useKeycloakInit({
    query: { enabled: false },
  });

  const handleLogin = async () => {
    const { data } = await refetch();

    if (data) {
      window.location.replace(data);
    }
  };

  const form = useTranslatedForm<typeof loginSchema>(loginSchema, {
    initialValues: {
      username: "",
      password: "",
    },
  });

  return (
    <>
      <Center py="xl">
        <Stack align="center" gap="xl" maw={400} w="100%" px="md">
          <div>
            <Title ta="center" order={1}>
              {t("company.login")}
            </Title>
            <Text ta="center" c="dimmed">
              {t("welcome")}
            </Text>
          </div>

          <Paper w="100%" p="xl" radius="md" withBorder>
            <form
              onSubmit={form.onSubmit((values) => {
                setError("");
                login({
                  data: {
                    username: values.username,
                    password: values.password,
                  },
                });
              })}
            >
              <Stack gap="md">
                {error && (
                  <Alert color="red" title={t("login.fail")}>
                    {t(error)}
                  </Alert>
                )}
                <TextInput
                  label={t("email.title")}
                  placeholder="your@email.com"
                  autoComplete="email"
                  leftSection={<IconMailSearch size={16} />}
                  {...form.getInputProps("username")}
                />
                <PasswordInput
                  label={t("register.password.title")}
                  placeholder="***********"
                  autoComplete="password"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("password")}
                />
                <Button
                  type="submit"
                  loading={isPending}
                  disabled={isPending}
                  size="md"
                >
                  {t("login.title")}
                </Button>
              </Stack>
            </form>
          </Paper>

          <Stack gap="sm" w="100%">
            <Button
              component={NavLink}
              to="/register"
              variant="light"
              size="sm"
            >
              {t("login.register.title")}
            </Button>
            <Button
              component={NavLink}
              to="/forget_password"
              variant="light"
              size="sm"
            >
              {t("forget_password.login")}
            </Button>
          </Stack>

          <Divider w="100%" label="or" labelPosition="center" />

          <Stack w="100%">
            <Text ta="center" size="sm" fw={500} mb="md">
              {t("keycloak.login")}
            </Text>
            <Button
              onClick={handleLogin}
              disabled={isFetching}
              size="md"
              fullWidth
            >
              {isFetching ? t("keycloak.redirecting") : t("keycloak.login")}
            </Button>
          </Stack>
        </Stack>
      </Center>
    </>
  );
};

export default Login;
