import {
  AppShell,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Outlet } from "react-router";
import Header from "../components/Header";
import Navbar from "../components/Navbar";

interface RootLayoutProps {
  navbarHidden: boolean;
}

export default function RootLayout({ navbarHidden }: RootLayoutProps) {
  const [mobileOpened, { toggle: toggleMobile }] = useDisclosure();
  const [desktopOpened, { toggle: toggleDesktop }] = useDisclosure(true);

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
                mobile: !mobileOpened,
                desktop: !desktopOpened,
              },
            }
          : undefined
      }
    >
      <Header
        showNavbar={!navbarHidden}
        mobileOpened={mobileOpened}
        desktopOpened={desktopOpened}
        toggleMobile={toggleMobile}
        toggleDesktop={toggleDesktop}
      />
      {!navbarHidden && <Navbar />}
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
