import { Center, Loader, Stack, Text } from "@mantine/core";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import serverData from "../utils/server-data";

const AuthLink = () => {
  const { t } = useTranslation();
  const { token = "" } = useParams<{ token: string }>();

  useEffect(() => {
    if (!token) return;
    window.location.replace(
      `${serverData.backendUrl}/api/auth/link/${encodeURIComponent(token)}`,
    );
  }, [token]);

  return (
    <Center py="xl">
      <Stack align="center" gap="md">
        <Loader />
        <Text c="dimmed" size="sm">
          {t("auth.link_redirecting")}
        </Text>
      </Stack>
    </Center>
  );
};
export default AuthLink;
