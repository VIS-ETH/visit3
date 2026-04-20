import {
  Button,
  TextInput,
  PasswordInput,
  Stack,
  Divider,
} from "@mantine/core";
import { IconLock, IconMailSearch } from "@tabler/icons-react";
import { NavLink, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";
import { setToken } from "../api/utils";
import type { Token } from "../orval/generated/fastAPI.schemas";
import { useKeycloakInit, useLoginUser } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";

const Login = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("login.title"));
  const navigate = useNavigate();

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: (data: Token) => {
        setToken(data.access_token);
        navigate("/");
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
    <AuthCardLayout title={t("company.login")} subtitle={t("welcome")}>
      <form
        onSubmit={form.onSubmit((values) => {
          login({
            data: {
              username: values.username,
              password: values.password,
            },
          });
        })}
      >
        <Stack gap="md">
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
            className="login-primary-button"
          >
            {t("login.title")}
          </Button>
        </Stack>
      </form>

      <Stack gap="sm" w="100%">
        <Button
          component={NavLink}
          to="/register"
          variant="light"
          size="sm"
          className="login-secondary-button"
        >
          {t("login.register.title")}
        </Button>
        <Button
          component={NavLink}
          to="/forget-password"
          variant="light"
          size="sm"
          className="login-secondary-button"
        >
          {t("forget_password.login")}
        </Button>
      </Stack>

      <Divider w="100%" label={t("common.or")} labelPosition="center" />

      <Button
        onClick={handleLogin}
        disabled={isFetching}
        size="md"
        fullWidth
        className="login-primary-button"
      >
        {isFetching ? t("keycloak.redirecting") : t("keycloak.login")}
      </Button>
    </AuthCardLayout>
  );
};

export default Login;
