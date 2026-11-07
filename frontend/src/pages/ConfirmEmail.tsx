import { useTranslation } from "react-i18next";
import { Navigate, useParams, useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  getGetCurrentUserQueryKey,
  useConfirmEmail,
  useValidateConfirmEmailToken,
} from "../orval/generated/user/user";
import { useCurrentUser } from "../context/useCurrentUser";
import { useAsyncAction } from "../hooks/use-async-action";
import {
  Button,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconMailCheck, IconMailX, IconArrowLeft } from "@tabler/icons-react";

const ConfirmEmail = () => {
  const { token } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const [isConfirmSuccess, setIsConfirmSuccess] = useState(false);
  const confirmToken = token?.trim() ?? "";

  const {
    data: isValid,
    isPending: isValidationPending,
    isError: isValidationError,
  } = useValidateConfirmEmailToken(confirmToken, {
    query: {
      enabled: Boolean(confirmToken),
      retry: false,
    },
  });

  const { mutateAsync: confirmEmail } = useConfirmEmail();

  const { run: confirm, isRunning: isConfirmPending } = useAsyncAction(
    async () => {
      await confirmEmail({ token: confirmToken });
      await queryClient.invalidateQueries({
        queryKey: getGetCurrentUserQueryKey(),
      });
      setIsConfirmSuccess(true);
    },
  );

  if (!confirmToken) {
    return <Navigate to="/login" replace />;
  }

  if (isValidationPending) {
    return (
      <Center>
        <Paper shadow="md" p="xl" radius="lg" maw={400} w="100%">
          <Stack align="center" gap="xl">
            <Loader size="lg" />
            <Stack gap="sm" align="center">
              <Title order={3}>{t("email.confirm.validating")}</Title>
              <Text c="dimmed" size="sm" ta="center">
                {t("email.confirm.please_wait")}
              </Text>
            </Stack>
          </Stack>
        </Paper>
      </Center>
    );
  }

  if (isValidationError || !isValid) {
    return (
      <Center>
        <Paper shadow="md" p="xl" radius="lg" maw={400} w="100%">
          <Stack gap="lg">
            <Stack align="center" gap="md">
              <IconMailX size={60} color="var(--mantine-color-red-6)" />
              <Stack gap="xs" align="center">
                <Title order={2}>{t("email.confirm.invalid")}</Title>
                <Text c="dimmed" size="sm" ta="center">
                  {t("email.confirm.link_expired")}
                </Text>
              </Stack>
            </Stack>
            <Button
              variant="light"
              fullWidth
              leftSection={<IconArrowLeft size={16} />}
              onClick={() => navigate("/login")}
            >
              {t("email.confirm.back_to_login")}
            </Button>
          </Stack>
        </Paper>
      </Center>
    );
  }

  if (isConfirmSuccess) {
    return (
      <Center>
        <Paper shadow="md" p="xl" radius="lg" maw={400} w="100%">
          <Stack gap="lg">
            <Stack align="center" gap="md">
              <IconMailCheck size={60} color="var(--mantine-color-green-6)" />
              <Stack gap="xs" align="center">
                <Title order={2}>{t("email.confirm.success")}</Title>
                <Text c="dimmed" size="sm" ta="center">
                  {t("email.confirm.success_description")}
                </Text>
              </Stack>
            </Stack>
            <Button
              fullWidth
              onClick={() => navigate(user ? "/" : "/login")}
              leftSection={<IconArrowLeft size={16} />}
            >
              {user ? t("nav.home") : t("email.confirm.go_to_login")}
            </Button>
          </Stack>
        </Paper>
      </Center>
    );
  }

  return (
    <Center>
      <Paper shadow="md" p="xl" radius="lg" maw={400} w="100%">
        <Stack gap="lg">
          <Stack align="center" gap="md">
            <IconMailCheck size={60} color="var(--mantine-color-blue-6)" />
            <Stack gap="xs" align="center">
              <Title order={2}>{t("email.confirm.title")}</Title>
              <Text c="dimmed" size="sm" ta="center">
                {t("email.confirm.description")}
              </Text>
            </Stack>
          </Stack>

          <Group grow>
            <Button
              variant="light"
              onClick={() => navigate("/login")}
              disabled={isConfirmPending}
            >
              {t("email.confirm.cancel")}
            </Button>
            <Button onClick={() => void confirm()} loading={isConfirmPending}>
              {t("email.confirm.confirm_button")}
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Center>
  );
};
export default ConfirmEmail;
