import { Center, Stack } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import IconTitle from "../components/IconTitle";

export default function UnconfirmedUser() {
  const { t } = useTranslation();

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
