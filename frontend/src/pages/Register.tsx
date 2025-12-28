import { useState } from "react";
import { Alert, Button, TextInput, PasswordInput, Stack } from "@mantine/core";
import type { AxiosError } from "axios";
import { useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useRegisterUser } from "../orval/generated/users/users";
import { useForm } from "@mantine/form";
import { zod4Resolver } from "mantine-form-zod-resolver";
import registerSchema from "../schemas/registerSchema";
import { useTranslation } from "react-i18next";
import { safeTranslate } from "../utils/utils";

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
          : "Server error";

        setError(message);
      },
    },
  });

  const form = useForm({
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
    validate: zod4Resolver(registerSchema),
  });

  return (
    <form
      onSubmit={form.onSubmit((values) => {
        setError("");
        register({ data: { email: values.email, password: values.password } });
      })}
    >
      <Stack>
        {error && (
          <Alert color="red" title={t("registration.fail")}>
            {error}
          </Alert>
        )}
        <TextInput
          label={t("register.email")}
          autoComplete="email"
          placeholder="your@email.com"
          error={safeTranslate(t, form.errors.email)}
          {...form.getInputProps("email")}
        />
        <PasswordInput
          label={t("register.password.title")}
          autoComplete="new-password"
          placeholder="************"
          error={safeTranslate(t, form.errors.password)}
          {...form.getInputProps("password")}
        />
        <PasswordInput
          label={t("register.password.confirm")}
          autoComplete="new-password"
          error={safeTranslate(t, form.errors.confirmPassword)}
          placeholder="************"
          {...form.getInputProps("confirmPassword")}
        />
        <Button type="submit" loading={isPending} disabled={isPending}>
          {t("register.button")}
        </Button>
      </Stack>
    </form>
  );
};

export default Register;
