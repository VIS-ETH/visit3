import { AppShell, Burger, Divider, Group, Title } from "@mantine/core";
import { NavLink } from "react-router";
import NavbarToggles from "./NavbarToggles";

interface HeaderProps {
  showNavbar: boolean;
  navbarOpened: boolean;
  toggleNavbar: () => void;
}

export default function Header({
  showNavbar,
  navbarOpened,
  toggleNavbar,
}: HeaderProps) {
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
            <Title order={3} px="lg" visibleFrom="sm" className="brand-title">
              VISIT
            </Title>
          </NavLink>
        </Group>
        <NavbarToggles />
      </Group>
    </AppShell.Header>
  );
}
