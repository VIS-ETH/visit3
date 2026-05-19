import { Button, Center, Stack, Text } from "@mantine/core";
import { IconMail } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useSendConfirmationMail } from "../orval/generated/user/user";
import IconTitle from "../components/IconTitle";
import { useCurrentUser } from "../context/useCurrentUser";

const UnconfirmedEmail = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useCurrentUser();
  const [emailSent, setEmailSent] = useState(false);

  useEffect(() => {
    if (user?.email_confirmed) navigate("/", { replace: true });
  }, [user?.email_confirmed, navigate]);

  const { mutate: send, isPending } = useSendConfirmationMail({
    mutation: {
      onSuccess: () => {
        setEmailSent(true);
      },
    },
  });

  if (!user) {
    return (
      <Center>
        <Stack align="center" gap="lg" maw={520}>
          <IconTitle
            icon={<IconMail size={50} />}
            title={t("email.confirm.login_required")}
            color="blue"
          />
          <Text ta="center" c="dimmed">
            {t("email.confirm.login_required_description")}
          </Text>
          <Button component={NavLink} to="/login">
            {t("email.confirm.go_to_login")}
          </Button>
        </Stack>
      </Center>
    );
  }

  return (
    <Center>
      {!emailSent ? (
        <Stack align="center" gap="lg">
          <IconTitle
            icon={<IconMail size={50} />}
            title={t("email.confirm.unconfirmed")}
            color="blue"
          />
          <Text ta="center" c="dimmed" maw={520}>
            {t("email.confirm.unconfirmed_description", { email: user.email })}
          </Text>
          <Button
            size="lg"
            disabled={isPending}
            onClick={() => {
              send();
            }}
          >
            {t("email.confirm.button")}
          </Button>
        </Stack>
      ) : (
        <Stack align="center" gap="lg">
          <IconTitle
            icon={<IconMail size={50} />}
            title={t("email.confirm.sent")}
            color="green"
          />
          <Text ta="center" c="dimmed" maw={520}>
            {t("email.confirm.sent_description", { email: user.email })}
          </Text>
        </Stack>
      )}
    </Center>
  );
};
export default UnconfirmedEmail;
