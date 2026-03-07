import { Button, Group, Image, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { useCurrentUser } from "../context/useCurrentUser";
import BackButton from "../components/BackButton";

export default function Kp() {
  const { user } = useCurrentUser();
  const { t } = useTranslation();

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <Title order={2}>{t("kp.title")}</Title>
      <Text>{t("kp.description")}</Text>
      <Group justify="flex-start" wrap="wrap" mt="xs">
        {user?.is_company && (
          <Button component={Link} to="/kp/join" w="fit-content">
            {t("kp.join_button")}
          </Button>
        )}
        {(user?.is_staff || user?.is_admin) && (
          <Button component={Link} to="/kp/dashboard" w="fit-content">
            {t("kp.dashboard_button")}
          </Button>
        )}
      </Group>
      <Image
        src="https://placehold.co/1200x600?text=Kontaktparty+Image+Placeholder"
        alt={t("kp.image_alt")}
        radius="md"
      />
    </Stack>
  );
}
