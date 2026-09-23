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
  IconInfoCircle,
  IconLock,
  IconMailSearch,
  IconPhone,
} from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import { useRegisterUser } from "../../orval/generated/auth/auth";
import { registerSchema } from "../../schemas/registerSchema";
import { useTranslatedForm } from "../../utils/translator";

interface CompanyJoinSignupProps {
  token: string;
  invitedEmail: string;
  loginHref: string;
}

const CompanyJoinSignup = ({
  token,
  invitedEmail,
  loginHref,
}: CompanyJoinSignupProps) => {
  const { t } = useTranslation();
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
      email: invitedEmail,
      password: "",
      confirmPassword: "",
      firstName: "",
      lastName: "",
      phoneNumber: "",
    },
  });

  if (registeredEmail) {
    return (
      <Stack w="100%" gap="md">
        <Alert color="green" icon={<IconCheck size={16} />}>
          {t("register.success.alert", { email: registeredEmail })}
        </Alert>
        <Text c="dimmed" size="sm">
          {t("register.invite.confirm_description")}
        </Text>
        <Button component={NavLink} to={loginHref}>
          {t("register.success.login")}
        </Button>
      </Stack>
    );
  }

  return (
    <Stack w="100%" gap="md">
      <Alert icon={<IconInfoCircle />} color="blue" variant="light">
        {t("register.invite.hint")}
      </Alert>
      <form
        onSubmit={form.onSubmit((values) => {
          register({
            data: {
              email: values.email,
              password: values.password,
              first_name: values.firstName.trim(),
              last_name: values.lastName.trim(),
              phone_number: values.phoneNumber?.trim() ?? undefined,
              invite_token: token,
            },
          });
        })}
      >
        <Stack gap="md">
          <TextInput
            label={t("register.first_name")}
            withAsterisk
            autoComplete="given-name"
            placeholder={t("register.first_name_placeholder")}
            {...form.getInputProps("firstName")}
          />
          <TextInput
            label={t("register.last_name")}
            withAsterisk
            autoComplete="family-name"
            placeholder={t("register.last_name_placeholder")}
            {...form.getInputProps("lastName")}
          />
          <TextInput
            label={t("register.phone_number")}
            autoComplete="tel"
            placeholder={t("register.phone_number_placeholder")}
            leftSection={<IconPhone size={16} />}
            {...form.getInputProps("phoneNumber")}
          />
          <TextInput
            label={t("email.title")}
            withAsterisk
            autoComplete="email"
            placeholder={t("register.email.placeholder")}
            leftSection={<IconMailSearch size={16} />}
            {...form.getInputProps("email")}
          />
          <PasswordInput
            label={t("register.password.title")}
            withAsterisk
            autoComplete="new-password"
            placeholder="************"
            leftSection={<IconLock size={16} />}
            {...form.getInputProps("password")}
          />
          <PasswordInput
            label={t("register.password.confirm")}
            withAsterisk
            autoComplete="new-password"
            placeholder="************"
            leftSection={<IconLock size={16} />}
            {...form.getInputProps("confirmPassword")}
          />
          <Button type="submit" loading={isPending} disabled={isPending}>
            {t("register.invite.submit")}
          </Button>
        </Stack>
      </form>
    </Stack>
  );
};

export default CompanyJoinSignup;
