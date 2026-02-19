import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router";
import {
  useConfirmEmail,
  useValidateConfirmEmailToken,
} from "../orval/generated/user/user";
import {
  Alert,
  Button,
  Center,
  Loader,
  Paper,
  Stack,
  Text,
} from "@mantine/core";
import { IconAlertCircle, IconMailCheck, IconMailX } from "@tabler/icons-react";
import IconTitle from "../components/IconTitle";

export default function ConfirmEmail() {
  const { token } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const {
    data: isValid,
    isPending: isValidationPending,
    isError: isValidationError,
  } = useValidateConfirmEmailToken(token || "", {
    query: {
      enabled: token !== undefined,
      retry: false,
    },
  });

  const {
    mutate: confirmEmail,
    isPending: isConfirmPending,
    isSuccess: isConfirmSuccess,
    isError: isConfirmError,
  } = useConfirmEmail();

  if (token === undefined) {
    navigate("/login");
    return;
  }

  if (isValidationPending) {
    return (
      <Center>
        <Paper radius="md" w="100%">
          <Stack align="center" gap="lg">
            <Loader />
            <Text c="dimmed">{t("keycloak.redirecting")}</Text>
          </Stack>
        </Paper>
      </Center>
    );
  }

  if (isValidationError || !isValid) {
    return (
      <Center>
        <Paper radius="md" w="100%">
          <Stack align="center" gap="lg">
            <IconTitle
              icon={<IconMailX size={50} />}
              title={t("email.confirm.invalid")}
              color="red"
              titleOrder={2}
            />
          </Stack>
        </Paper>
      </Center>
    );
  }

  if (isConfirmSuccess) {
    return (
      <Center>
        <Paper radius="md" w="100%">
          <Stack align="center" gap="lg">
            <IconTitle
              icon={<IconMailCheck size={50} />}
              title={t("email.confirm.success")}
              color="green"
              titleOrder={2}
            />
          </Stack>
        </Paper>
      </Center>
    );
  }

  return (
    <Center>
      <Paper radius="md" w="100%">
        <Stack align="center" gap="lg">
          <IconTitle
            icon={<IconMailCheck size={50} />}
            title={t("email.confirm.unconfirmed")}
            color="blue"
            titleOrder={2}
          />
          {isConfirmError && (
            <Alert
              icon={<IconAlertCircle />}
              color="red"
              title={t("server.error")}
            >
              {t("email.confirm.error")}
            </Alert>
          )}
          <Button
            fullWidth
            onClick={() => confirmEmail({ token: token || "" })}
            loading={isConfirmPending}
          >
            {t("email.confirm.confirm_button")}
          </Button>
        </Stack>
      </Paper>
    </Center>
  );
}
