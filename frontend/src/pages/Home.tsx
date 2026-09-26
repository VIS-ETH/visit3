import { Badge, Group, Stack, Title } from "@mantine/core";
import { useCurrentUser } from "../context/useCurrentUser";
import LinkFeatureCard from "../components/LinkFeatureCard";
import { eventBannerImage } from "../components/home/kontaktparty-banner";
import { useGetLatestKp } from "../orval/generated/kp/kp";
import { useTranslation } from "react-i18next";

const Home = () => {
  const { user } = useCurrentUser();
  const { t } = useTranslation();
  const { data: latestKp, isPending } = useGetLatestKp();

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
      </Stack>

      <LinkFeatureCard
        to="/kp"
        image={eventBannerImage(latestKp?.banner)}
        imageLoading={isPending}
        imageAlt={t("home.kp.image_alt")}
        title={t("home.kp.title")}
        description={t("home.kp.description")}
      />
    </Stack>
  );
};
export default Home;
