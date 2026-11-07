import { Card, Group, Text, Title } from "@mantine/core";
import { IconArmchair } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import KpBookingServiceGrid from "./KpBookingServiceGrid";
import type { ServiceStepProps } from "./KpBookingServiceGrid";

const KpBookingBoothStep = (props: ServiceStepProps) => {
  const { t } = useTranslation();

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Group gap="sm" mb="sm">
        <IconArmchair size={20} />
        <Title order={4}>{t("kp.booking.booth_title")}</Title>
      </Group>
      <Text c="dimmed" size="sm">
        {t("kp.booking.booth_description")}
      </Text>
      <KpBookingServiceGrid
        {...props}
        emptyLabel={t("kp.booking.booth_none_available")}
      />
    </Card>
  );
};

export default KpBookingBoothStep;
