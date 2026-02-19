import { Alert, Center, Loader, Paper, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useReadUsersMe } from "../orval/generated/user/user";

function getFullName(firstName?: string | null, lastName?: string | null) {
  const fullName = `${firstName ?? ""} ${lastName ?? ""}`.trim();
  return fullName.length > 0 ? fullName : "-";
}

export default function Profile() {
  const { t } = useTranslation();
  const { data: user, isLoading, isError } = useReadUsersMe();

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError || !user) {
    return (
      <Center py="xl">
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("profile.load_error")}
        </Alert>
      </Center>
    );
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={700} gap="lg">
        <Title order={2}>{t("profile.title")}</Title>
        <Paper withBorder p="md" radius="md">
          <Stack gap="sm">
            <Text><Text span fw={600}>{t("profile.name")}: </Text>{getFullName(user.first_name, user.last_name)}</Text>
            <Text><Text span fw={600}>{t("profile.email")}: </Text>{user.email}</Text>
            <Text><Text span fw={600}>{t("profile.phone")}: </Text>{user.phone_number ?? "-"}</Text>
            <Text><Text span fw={600}>{t("profile.company")}: </Text>{user.company?.name ?? "-"}</Text>
          </Stack>
        </Paper>
      </Stack>
    </Center>
  );
}
