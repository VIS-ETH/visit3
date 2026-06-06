import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router";
import {
  useConfirmEmail,
  useValidateConfirmEmailToken,
} from "../orval/generated/user/user";
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

  const {
    mutate: confirmEmail,
    isPending: isConfirmPending,
    isSuccess: isConfirmSuccess,
  } = useConfirmEmail();

  if (!confirmToken) {
    navigate("/login");
    return;
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
              onClick={() => navigate("/login")}
              leftSection={<IconArrowLeft size={16} />}
            >
              {t("email.confirm.go_to_login")}
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
            <Button
              onClick={() => confirmEmail({ token: confirmToken })}
              loading={isConfirmPending}
            >
              {t("email.confirm.confirm_button")}
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Center>
  );
};
export default ConfirmEmail;
