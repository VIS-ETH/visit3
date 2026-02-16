import { AppShell, Burger, Divider, Group, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import NavbarToggles from "./NavbarToggles";

interface HeaderProps {
  showNavbar: boolean;
  mobileOpened: boolean;
  desktopOpened: boolean;
  toggleMobile: () => void;
  toggleDesktop: () => void;
}

export default function Header({
  showNavbar,
  mobileOpened,
  desktopOpened,
  toggleMobile,
  toggleDesktop,
}: HeaderProps) {
  const { t } = useTranslation();

  return (
    <AppShell.Header>
      <Group h="100%" px="md" justify="space-between" wrap="nowrap" gap="xs">
        <Group h="100%" gap="xs" wrap="nowrap">
          {showNavbar && (
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
              <Divider orientation="vertical" my="sm" />
            </>
          )}
          <Title order={3} px="lg" visibleFrom="sm">
            {t("welcome")}
          </Title>
        </Group>
        <NavbarToggles />
      </Group>
    </AppShell.Header>
  );
}
