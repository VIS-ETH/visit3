import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  TextInput,
  PasswordInput,
  Stack,
  Center,
  Paper,
  Title,
  Group,
  Box,
  ActionIcon,
} from "@mantine/core";
import type { AxiosError } from "axios";
import { NavLink, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useRegisterUser } from "../orval/generated/users/users";
import { registerSchema } from "../schemas/registerSchema";
import { useTranslation } from "react-i18next";
import { IconArrowBackUp } from "@tabler/icons-react";
import { useTranslatedForm } from "../utils/translator";

const Register = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("register.title"));
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const { mutate: register, isPending } = useRegisterUser({
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

  const form = useTranslatedForm<typeof registerSchema>(registerSchema, {
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  return (
    <Box pos="relative">
      <ActionIcon
        size="input-md"
        component={NavLink}
        to="/login"
        variant=""
        left="0"
        top="0"
        pos="absolute"
      >
        <IconArrowBackUp />
      </ActionIcon>
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
                label={t("register.email.title")}
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
    </Box>
  );
};

export default Register;
