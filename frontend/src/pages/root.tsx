import { AppShell } from "@mantine/core";
import { useEffect, useState } from "react";
import { Outlet } from "react-router";
import Header from "../components/Header";
import Navbar from "../components/Navbar";
import { readSessionBool, setSessionBool } from "../utils/session-storage";

interface RootLayoutProps {
  navbarHidden: boolean;
}

const NAVBAR_OPEN_KEY = "visit-navbar-open";
const MOBILE_MEDIA_QUERY = "(max-width: 48em)";

const defaultNavbarOpen = () => {
  if (typeof window === "undefined") return true;
  return !window.matchMedia(MOBILE_MEDIA_QUERY).matches;
};

export default function RootLayout({ navbarHidden }: RootLayoutProps) {
  const [navbarOpened, setNavbarOpened] = useState<boolean>(() =>
    readSessionBool(NAVBAR_OPEN_KEY, defaultNavbarOpen())
  );

  const toggleNavbar = () => {
    setNavbarOpened((previous) => !previous);
  };

  useEffect(() => {
    setSessionBool(NAVBAR_OPEN_KEY, navbarOpened);
  }, [navbarOpened]);

  return (
    <AppShell
      header={{ height: 60 }}
      padding="md"
      navbar={
        !navbarHidden
          ? {
              width: 300,
              breakpoint: "sm",
              collapsed: {
                mobile: !navbarOpened,
                desktop: !navbarOpened,
              },
            }
          : undefined
      }
    >
      <Header
        showNavbar={!navbarHidden}
        navbarOpened={navbarOpened}
        toggleNavbar={toggleNavbar}
      />
      {!navbarHidden && <Navbar />}
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
