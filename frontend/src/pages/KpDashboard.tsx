import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";

export default function KpDashboard() {
  const { t } = useTranslation();

  return (
    <Stack gap="md">
      <BackButton to="/kp" />
      <Title order={2}>{t("kp.dashboard.title")}</Title>
      <Text>{t("kp.dashboard.description")}</Text>
    </Stack>
  );
}
