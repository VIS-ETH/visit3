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
import { IconHome2, IconLogout2 } from "@tabler/icons-react";
import { useDisclosure } from "@mantine/hooks";
import { NavLink, Outlet, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useLogoutUser } from "../orval/generated/users/users";
import NavbarToggles from "../components/NavbarToggles";
import { clearToken } from "../api/auth";

interface RootLayoutProps {
  navbarHidden: boolean;
}

export default function RootLayout({ navbarHidden }: RootLayoutProps) {
  const [mobileOpened, { toggle: toggleMobile }] = useDisclosure();
  const [desktopOpened, { toggle: toggleDesktop }] = useDisclosure(true);
  const navigate = useNavigate();

  const { mutate: logout } = useLogoutUser({
    mutation: {
      onSuccess: () => {
        navigate("/login");
        clearToken();
      },
    },
  });

  const { t } = useTranslation();

  return (
    <AppShell
      header={{ height: 60 }}
      padding="md"
      navbar={{
        width: 300,
        breakpoint: "sm",
        collapsed: {
          mobile: !mobileOpened || navbarHidden,
          desktop: !desktopOpened || navbarHidden,
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group h="100%" px="md">
            {!navbarHidden && (
              <>
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
              </>
            )}
            <Title order={3} px="lg">
              {t("welcome")}
            </Title>
          </Group>
          <NavbarToggles />
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        <Stack m="sm" align="stretch">
          <Group align="center" gap="xs" mb="xs">
            <Text fw={700} size="xl" ta="center" w="100%">
              VISIT
            </Text>
          </Group>
          <Divider my="xs" label="Navigation" labelPosition="center" />
          <Stack gap="xs">
            <Button component={NavLink} to="/" leftSection={<IconHome2 />}>
              Home
            </Button>
            <Button
              onClick={() => {
                logout();
              }}
              leftSection={<IconLogout2 />}
            >
              Logout
            </Button>
          </Stack>
        </Stack>
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
