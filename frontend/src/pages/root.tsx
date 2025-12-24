import {
  AppShell,
  Burger,
  Divider,
  Group,
  Stack,
  Title,
  Button,
  Text,
} from "@mantine/core";
import {
  IconHome2,
  IconInfoCircle,
  IconFolder,
  IconLink,
} from "@tabler/icons-react";
import { useDisclosure } from "@mantine/hooks";
import ColorSchemeToggle from "../components/ColorSchemeToggle";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";

const navLinks = [
  { label: "Home", to: "/", icon: IconHome2 },
  { label: "Files", to: "/~/files", icon: IconFolder },
  { label: "Links", to: "/~/links", icon: IconLink },
  { label: "About", to: "/about", icon: IconInfoCircle },
];

export default function RootLayout() {
  const [mobileOpened, { toggle: toggleMobile }] = useDisclosure();
  const [desktopOpened, { toggle: toggleDesktop }] = useDisclosure(true);

  const { t, i18n } = useTranslation();

  const changeLanguage = () => {
    const lng = i18n.language;
    if (lng === "en") {
      i18n.changeLanguage("de");
    } else {
      i18n.changeLanguage("en");
    }
  };

  return (
    <AppShell
      header={{ height: 60 }}
      padding="md"
      navbar={{
        width: 300,
        breakpoint: "sm",
        collapsed: {
          mobile: !mobileOpened,
          desktop: !desktopOpened,
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group h="100%" px="md">
            <Burger
              opened={mobileOpened}
              onClick={toggleMobile}
              hiddenFrom="sm"
              size="sm"
            />
            <Burger
              opened={desktopOpened}
              onClick={toggleDesktop}
              visibleFrom="sm"
              size="sm"
            />
            <div></div>
            <Divider orientation="vertical" my="sm" />
            <Title order={3} px="lg">
              {t("welcome")}
            </Title>
          </Group>
          <ColorSchemeToggle />
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        <Stack m="sm" align="stretch">
          <Group align="center" gap="xs" mb="xs">
            <Text fw={700} size="xl" ta="center" w="100%">
              CDN Dashboard
            </Text>
          </Group>
          <Text size="sm" c="dimmed" m="sm" ml={2} ta="center" w="100%">
            Fast, reliable file delivery
          </Text>
          <Button onClick={changeLanguage}>{t("language-change")}</Button>
          <Divider my="xs" label="Navigation" labelPosition="center" />
          <Stack gap="xs">
            {navLinks.map(({ label, to, icon: Icon }) => (
              <Button
                key={to}
                component={NavLink}
                to={to}
                variant="filled"
                leftSection={<Icon size={28} />}
                fullWidth
                radius="md"
              >
                {label}
              </Button>
            ))}
          </Stack>
        </Stack>
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
