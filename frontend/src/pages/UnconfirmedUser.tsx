import { Center, Stack } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import IconTitle from "../components/IconTitle";
import { useCurrentUser } from "../context/useCurrentUser";

export default function UnconfirmedUser() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useCurrentUser();

  useEffect(() => {
    if (user?.user_confirmed) navigate("/", { replace: true });
  }, [user?.user_confirmed, navigate]);

  return (
    <Center>
      <Stack align="center" gap="lg">
        <IconTitle
          icon={<IconClock size={50} />}
          title={t("user.unconfirmed")}
          color="orange"
        />
      </Stack>
    </Center>
  );
}
