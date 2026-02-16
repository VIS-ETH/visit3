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
  Text,
} from "@mantine/core";
import { IconMailSearch, IconLock } from "@tabler/icons-react";
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
      <Center py="xl">
        <Stack align="center" gap="xl" maw={600} w="90%" px="md">
          <div>
            <Title ta="center" order={1}>
              {t("register.title")}
            </Title>
            <Text ta="center" c="dimmed" size="sm">
              {t("welcome")}
            </Text>
          </div>

          <Paper w="100%" p="xl" radius="md" withBorder>
            <form
              onSubmit={form.onSubmit((values) => {
                setError("");
                register({
                  data: { email: values.email, password: values.password },
                });
              })}
            >
              <Stack gap="md">
                {error && (
                  <Alert color="red" title={t("register.fail")}>
                    {t(error)}
                  </Alert>
                )}
                <TextInput
                  label={t("email.title")}
                  autoComplete="email"
                  placeholder={t("register.email.placeholder")}
                  leftSection={<IconMailSearch size={16} />}
                  {...form.getInputProps("email")}
                />
                <PasswordInput
                  label={t("register.password.title")}
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("password")}
                />
                <PasswordInput
                  label={t("register.password.confirm")}
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("confirmPassword")}
                />
                <Button
                  type="submit"
                  loading={isPending}
                  disabled={isPending}
                  size="md"
                >
                  {t("register.button")}
                </Button>
              </Stack>
            </form>
          </Paper>
        </Stack>
      </Center>
    </>
  );
};

export default Register;
