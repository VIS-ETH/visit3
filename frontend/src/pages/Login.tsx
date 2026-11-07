import { TextInput, PasswordInput, Stack, Divider } from "@mantine/core";
import { IconLock, IconMailSearch } from "@tabler/icons-react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { clearAuthState, clearLoggedOut, setToken } from "../api/utils";
import { useKeycloakInit, useLoginUser } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import ErrorAlert from "../components/ErrorAlert";
import { useAsyncAction } from "../hooks/use-async-action";
import { getSafeNextPath, rememberLoginNext } from "../utils/navigation";

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

  const { mutateAsync: login } = useLoginUser();

  const { run: submitLogin, isRunning: isLoggingIn } = useAsyncAction(
    async (username: string, password: string) => {
      const data = await login({ data: { username, password } });
      clearAuthState();
      queryClient.clear();
      rememberLoginNext(null);
      setToken(data.access_token);
      navigate(nextPath ?? "/");
    },
  );

  const { refetch, isFetching } = useKeycloakInit({
    query: { enabled: false },
  });

  const handleLogin = async () => {
    const { data } = await refetch();

    if (data) {
      clearAuthState();
      clearLoggedOut();
      queryClient.clear();
      rememberLoginNext(nextPath);
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
    <AuthCardLayout title={t("company.login")} maxWidth={620}>
      {callbackErrorKey ? <ErrorAlert>{t(callbackErrorKey)}</ErrorAlert> : null}

      <form
        onSubmit={form.onSubmit(
          (values) => void submitLogin(values.username.trim(), values.password),
        )}
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
          <AuthButton
            type="submit"
            loading={isLoggingIn}
            disabled={isLoggingIn}
          >
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
