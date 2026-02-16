import { Center, Stack, Alert } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

interface NotAllowedProps {
  titleKey?: string;
  descriptionKey?: string;
}

export default function NotAllowed({
  titleKey = "not_allowed.title",
  descriptionKey = "not_allowed.description",
}: NotAllowedProps) {
  const { t } = useTranslation();

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1000} gap="lg">
        <Alert icon={<IconAlertCircle />} color="red" title={t(titleKey)}>
          {t(descriptionKey)}
        </Alert>
      </Stack>
    </Center>
  );
}
