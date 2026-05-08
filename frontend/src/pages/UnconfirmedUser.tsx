import { Button, Center, Stack, Text } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useEffect } from "react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import IconTitle from "../components/IconTitle";
import { useCurrentUser } from "../context/useCurrentUser";

const UnconfirmedUser = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useCurrentUser();

  useEffect(() => {
    if (user?.user_confirmed) navigate("/", { replace: true });
  }, [user?.user_confirmed, navigate]);

  if (!user) {
    return (
      <Center>
        <Stack align="center" gap="lg" maw={520}>
          <IconTitle
            icon={<IconClock size={50} />}
            title={t("user.unconfirmed_login_required")}
            color="yellow"
          />
          <Text ta="center" c="dimmed">
            {t("user.unconfirmed_login_required_description")}
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
      <Stack align="center" gap="lg" maw={520}>
        <IconTitle
          icon={<IconClock size={50} />}
          title={t("user.unconfirmed")}
          color="yellow"
        />
        <Text ta="center" c="dimmed">
          {t("user.unconfirmed_description")}
        </Text>
      </Stack>
    </Center>
  );
};
export default UnconfirmedUser;
