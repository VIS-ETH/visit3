import { Center, Title, Stack, ThemeIcon } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

export default function UnconfirmedEmail() {
  const { t } = useTranslation();

  return (
    <Center>
      <Stack align="center" gap="lg">
        <ThemeIcon size={80} radius="xl" variant="light" color="orange">
          <IconClock size={50} />
        </ThemeIcon>
        <Title ta="center">{t("user.unconfirmed")}</Title>
      </Stack>
    </Center>
  );
}
