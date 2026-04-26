import {
  Alert,
  Button,
  PasswordInput,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import {
  IconCheck,
  IconLock,
  IconMailSearch,
  IconPhone,
} from "@tabler/icons-react";
import { NavLink, useLocation } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useState } from "react";
import { registerSchema } from "../schemas/registerSchema";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import { useRegisterUser } from "../orval/generated/auth/auth";
import AuthCardLayout from "../components/AuthCardLayout";
import AuthButton from "../components/AuthButton";
import { getSafeNextPath } from "../utils/navigation";

const Register = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("register.title"));
  const location = useLocation();
  const nextPath = getSafeNextPath(location.search);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const { mutate: register, isPending } = useRegisterUser({
    mutation: {
      onSuccess: (_user, variables) => {
        setRegisteredEmail(variables.data.email);
      },
    },
  });

  const form = useTranslatedForm<typeof registerSchema>(registerSchema, {
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
      firstName: "",
      lastName: "",
      phoneNumber: "",
    },
  });

  return (
    <AuthCardLayout
      title={
        registeredEmail ? t("register.success.title") : t("register.title")
      }
      subtitle={registeredEmail ? t("register.success.subtitle") : t("welcome")}
      maxWidth={620}
      backTo="/login"
    >
      {registeredEmail ? (
        <Stack gap="md">
          <Alert color="green" icon={<IconCheck size={16} />}>
            {t("register.success.alert", { email: registeredEmail })}
          </Alert>
          <Text c="dimmed" size="sm">
            {t("register.success.description")}
          </Text>
          <AuthButton
            component={NavLink}
            to={
              nextPath
                ? `/login?next=${encodeURIComponent(nextPath)}`
                : "/login"
            }
          >
            {t("register.success.login")}
          </AuthButton>
          <Button
            variant="light"
            onClick={() => {
              setRegisteredEmail(null);
              form.reset();
            }}
          >
            {t("register.success.register_another")}
          </Button>
        </Stack>
      ) : (
        <form
          onSubmit={form.onSubmit((values) => {
            register({
              data: {
                email: values.email,
                password: values.password,
                first_name: values.firstName?.trim(),
                last_name: values.lastName?.trim(),
                phone_number: values.phoneNumber?.trim() || undefined,
              },
            });
          })}
        >
          <Stack gap="md">
            <TextInput
              label={t("register.first_name")}
              withAsterisk
              autoComplete="given-name"
              size="md"
              placeholder={t("register.first_name_placeholder")}
              {...form.getInputProps("firstName")}
            />
            <TextInput
              label={t("register.last_name")}
              withAsterisk
              autoComplete="family-name"
              size="md"
              placeholder={t("register.last_name_placeholder")}
              {...form.getInputProps("lastName")}
            />
            <TextInput
              label={t("register.phone_number")}
              autoComplete="tel"
              size="md"
              placeholder={t("register.phone_number_placeholder")}
              leftSection={<IconPhone size={16} />}
              {...form.getInputProps("phoneNumber")}
            />
            <TextInput
              label={t("email.title")}
              withAsterisk
              autoComplete="email"
              size="md"
              placeholder={t("register.email.placeholder")}
              leftSection={<IconMailSearch size={16} />}
              {...form.getInputProps("email")}
            />
            <PasswordInput
              label={t("register.password.title")}
              withAsterisk
              autoComplete="new-password"
              size="md"
              placeholder="************"
              leftSection={<IconLock size={16} />}
              {...form.getInputProps("password")}
            />
            <PasswordInput
              label={t("register.password.confirm")}
              withAsterisk
              autoComplete="new-password"
              size="md"
              placeholder="************"
              leftSection={<IconLock size={16} />}
              {...form.getInputProps("confirmPassword")}
            />
            <AuthButton type="submit" loading={isPending} disabled={isPending}>
              {t("register.button")}
            </AuthButton>
          </Stack>
        </form>
      )}
    </AuthCardLayout>
  );
};

export default Register;
