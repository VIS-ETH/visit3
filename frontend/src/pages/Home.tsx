import { Badge, Group, Stack, Text, Title } from "@mantine/core";
import { useCurrentUser } from "../context/useCurrentUser";
import LinkFeatureCard from "../components/LinkFeatureCard";
import { useTranslation } from "react-i18next";

const Home = () => {
  const { user } = useCurrentUser();
  const { t } = useTranslation();

  return (
    <Stack gap="md">
      <Stack className="home-hero" gap={6}>
        <Group justify="space-between" align="center" wrap="wrap">
          <Title order={3} className="section-title">
            {t("home.welcome_name", { name: user?.first_name ?? "" })}
          </Title>
          <Badge variant="light" color="brand" radius="sm">
            {t("home.portal_badge")}
          </Badge>
        </Group>
        <Text c="dimmed" size="sm">
          {t("home.subtitle")}
        </Text>
      </Stack>

      <LinkFeatureCard
        to="/kp"
        imageSrc="https://placehold.co/1200x600?text=Kontaktparty"
        imageAlt={t("home.kp.image_alt")}
        title={t("home.kp.title")}
        description={t("home.kp.description")}
      />
    </Stack>
  );
};
export default Home;
