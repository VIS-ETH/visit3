import { TextInput, PasswordInput, Stack, Divider, Alert } from "@mantine/core";
import { IconAlertCircle, IconLock, IconMailSearch } from "@tabler/icons-react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { clearAuthState, setToken } from "../api/utils";
import type { Token } from "../orval/generated/fastAPI.schemas";
import { useKeycloakInit, useLoginUser } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import { getSafeNextPath } from "../utils/navigation";

const CALLBACK_ERROR_CODES = new Set([
  "auth.email_taken_locally",
  "auth.not_vis_member",
  "auth.link_invalid",
]);

const getCallbackErrorKey = (search: string) => {
  const code = new URLSearchParams(search).get("error");
  if (!code) return null;
  return CALLBACK_ERROR_CODES.has(code) ? code : "server.error";
};

const Login = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("login.title"));
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const nextPath = getSafeNextPath(location.search);
  const callbackErrorKey = getCallbackErrorKey(location.search);

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: (data: Token) => {
        clearAuthState();
        queryClient.clear();
        setToken(data.access_token);
        navigate(nextPath ?? "/");
      },
    },
  });

  const { refetch, isFetching } = useKeycloakInit({
    query: { enabled: false },
  });

  const handleLogin = async () => {
    const { data } = await refetch();

    if (data) {
      clearAuthState();
      queryClient.clear();
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
    <AuthCardLayout
      title={t("company.login")}
      maxWidth={620}
    >
      {callbackErrorKey ? (
        <Alert
          icon={<IconAlertCircle />}
          color="red"
          title={t("error.title")}
          w="100%"
        >
          {t(callbackErrorKey)}
        </Alert>
      ) : null}

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
            placeholder={t("register.email.placeholder")}
            autoComplete="email"
            size="md"
            leftSection={<IconMailSearch size={16} />}
            {...form.getInputProps("username")}
          />
          <PasswordInput
            label={t("register.password.title")}
            placeholder="***********"
            autoComplete="password"
            size="md"
            leftSection={<IconLock size={16} />}
            {...form.getInputProps("password")}
          />
          <AuthButton type="submit" loading={isPending} disabled={isPending}>
            {t("login.title")}
          </AuthButton>
        </Stack>
      </form>

      <Stack gap="sm" w="100%">
        <AuthButton
          component={NavLink}
          to={
            nextPath
              ? `/register?next=${encodeURIComponent(nextPath)}`
              : "/register"
          }
          intent="secondary"
        >
          {t("login.register.title")}
        </AuthButton>
        <AuthButton component={NavLink} to="/reset-password" intent="secondary">
          {t("password_reset_request.login")}
        </AuthButton>
      </Stack>

      <Divider
        w="100%"
        label={t("register.company.or")}
        labelPosition="center"
      />

      <AuthButton onClick={handleLogin} disabled={isFetching}>
        {isFetching ? t("keycloak.redirecting") : t("keycloak.login")}
      </AuthButton>
    </AuthCardLayout>
  );
};

export default Login;
