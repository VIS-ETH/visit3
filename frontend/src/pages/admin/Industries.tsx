import { Center, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import IndustriesTab from "../../components/IndustriesTab";

const Industries = () => {
  const { t } = useTranslation();

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={900} gap="lg">
        <Title order={2}>{t("industries.page_title")}</Title>
        <Text c="dimmed" size="sm">
          {t("industries.page_subtitle")}
        </Text>
        <IndustriesTab />
      </Stack>
    </Center>
  );
};

export default Industries;
