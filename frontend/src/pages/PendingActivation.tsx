import { Center, Stack } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import IconTitle from "../components/IconTitle";

const PendingActivation = () => {
  const { t } = useTranslation();

  return (
    <Center>
      <Stack align="center" gap="lg" maw={520}>
        <IconTitle
          icon={<IconClock size={50} />}
          title={t("user.pending_activation")}
          color="yellow"
        />
      </Stack>
    </Center>
  );
};
export default PendingActivation;
