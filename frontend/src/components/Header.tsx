import { AppShell, Burger, Divider, Group, Image, Title } from "@mantine/core";
import { NavLink } from "react-router";
import NavbarToggles from "./NavbarToggles";

interface HeaderProps {
  showNavbar: boolean;
  navbarOpened: boolean;
  toggleNavbar: () => void;
}

const Header = ({ showNavbar, navbarOpened, toggleNavbar }: HeaderProps) => {
  return (
    <AppShell.Header className="app-header">
      <Group h="100%" px="md" justify="space-between" wrap="nowrap" gap="xs">
        <Group h="100%" gap="xs" wrap="nowrap">
          {showNavbar && (
            <>
              <Burger
                opened={navbarOpened}
                onClick={toggleNavbar}
                hiddenFrom="sm"
                size="sm"
              />
              <Burger
                opened={navbarOpened}
                onClick={toggleNavbar}
                visibleFrom="sm"
                size="sm"
              />
              <Divider orientation="vertical" my="sm" />
            </>
          )}
          <NavLink to="/" style={{ textDecoration: "none", color: "inherit" }}>
            <Group gap="sm" px="lg" wrap="nowrap">
              <Image src="/brand/vis-signet.svg" alt="VIS" h={32} w={32} />
              <Title order={3} visibleFrom="sm" className="brand-title">
                VISIT
              </Title>
            </Group>
          </NavLink>
        </Group>
        <NavbarToggles />
      </Group>
    </AppShell.Header>
  );
};
export default Header;
