import { Alert, Card, Group, Text, Title } from "@mantine/core";
import { IconClipboardList, IconInfoCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import KpBookingServiceGrid from "./KpBookingServiceGrid";
import type { ServiceStepProps } from "./KpBookingServiceGrid";

const KpBookingServicesStep = (props: ServiceStepProps) => {
  const { t } = useTranslation();

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Group gap="sm" mb="sm">
        <IconClipboardList size={20} />
        <Title order={4}>{t("kp.booking.services_title")}</Title>
      </Group>

      <Alert icon={<IconInfoCircle />} color="orange" variant="light">
        <Text size="sm">{t("kp.booking.services_policy")}</Text>
      </Alert>
      <KpBookingServiceGrid
        {...props}
        emptyLabel={t("kp.booking.services_none_available")}
      />
    </Card>
  );
};

export default KpBookingServicesStep;
