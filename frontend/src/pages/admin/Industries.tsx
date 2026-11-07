import { Center, Stack, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import IndustriesTab from "../../components/kp-manage/IndustriesTab";

const Industries = () => {
  const { t } = useTranslation();

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={900} gap="lg">
        <Title order={2}>{t("industries.page_title")}</Title>
        <IndustriesTab />
      </Stack>
    </Center>
  );
};

export default Industries;
