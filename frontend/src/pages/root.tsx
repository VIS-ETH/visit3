import { Alert, AppShell, Button } from "@mantine/core";
import { useEffect, useState } from "react";
import { Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import Header from "../components/Header";
import Navbar from "../components/Navbar";
import { readSessionBool, setSessionBool } from "../utils/session-storage";
import {
  clearImpersonation,
  getImpersonatingDisplayName,
  isImpersonating,
} from "../api/utils";
import { getGetCurrentUserQueryKey } from "../orval/generated/user/user";

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
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [navbarOpened, setNavbarOpened] = useState<boolean>(() =>
    readSessionBool(NAVBAR_OPEN_KEY, defaultNavbarOpen()),
  );
  const [impersonating, setImpersonating] = useState(isImpersonating);
  const [displayName, setDisplayName] = useState(getImpersonatingDisplayName);

  const toggleNavbar = () => {
    setNavbarOpened((previous) => !previous);
  };

  useEffect(() => {
    setSessionBool(NAVBAR_OPEN_KEY, navbarOpened);
  }, [navbarOpened]);

  useEffect(() => {
    const handler = () => {
      setImpersonating(isImpersonating());
      setDisplayName(getImpersonatingDisplayName());
    };
    window.addEventListener("impersonation-changed", handler);
    return () => window.removeEventListener("impersonation-changed", handler);
  }, []);

  const handleStopImpersonating = () => {
    clearImpersonation();
    queryClient.invalidateQueries({ queryKey: getGetCurrentUserQueryKey() });
  };

  return (
    <AppShell
      className="app-shell"
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
      <AppShell.Main className="app-main">
        {!navbarHidden && impersonating && (
          <Alert
            color="yellow"
            mb="md"
            title={t("impersonation.banner_title", { name: displayName })}
          >
            <Button size="xs" color="yellow" onClick={handleStopImpersonating}>
              {t("impersonation.stop")}
            </Button>
          </Alert>
        )}
        <div className="page-wrap">
          <Outlet />
        </div>
      </AppShell.Main>
    </AppShell>
  );
}
