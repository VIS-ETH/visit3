import { TextInput, PasswordInput, Stack, Divider } from "@mantine/core";
import { IconLock, IconMailSearch } from "@tabler/icons-react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useTranslatedForm } from "../utils/translator";
import { loginSchema } from "../schemas/loginSchema";
import { useTranslation } from "react-i18next";
import { setToken } from "../api/utils";
import type { Token } from "../orval/generated/fastAPI.schemas";
import { useKeycloakInit, useLoginUser } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import { getSafeNextPath } from "../utils/navigation";

const Login = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("login.title"));
  const navigate = useNavigate();
  const location = useLocation();
  const nextPath = getSafeNextPath(location.search);

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: (data: Token) => {
        setToken(data.access_token);
        navigate(nextPath || "/");
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
    <AuthCardLayout
      title={t("company.login")}
      subtitle={t("welcome")}
      maxWidth={620}
    >
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
        <AuthButton
          component={NavLink}
          to="/forget-password"
          intent="secondary"
        >
          {t("forget_password.login")}
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
