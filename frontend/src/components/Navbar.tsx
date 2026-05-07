import {
  Anchor,
  AppShell,
  Button,
  Divider,
  Group,
  Image,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconBuilding,
  IconCalendarEvent,
  IconHome2,
  IconLogout2,
  IconSettings,
  IconUser,
} from "@tabler/icons-react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { clearToken } from "../api/utils";
import { useLogoutUser } from "../orval/generated/user/user";
import { useCurrentUser } from "../context/useCurrentUser";
import serverData from "../utils/server-data";

export default function Navbar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useCurrentUser();

  const { mutate: logout } = useLogoutUser({
    mutation: {
      onSuccess: () => {
        navigate("/login");
        clearToken();
      },
    },
  });

  return (
    <AppShell.Navbar p="md" className="app-navbar">
      <Stack m="sm" align="stretch">
        <Group justify="center" align="center" gap="xs" mb="xs" wrap="nowrap">
          <Image
            src={`${serverData.staticBase}favicon.ico`}
            alt={t("nav.vis_logo_alt")}
            h={22}
            w={22}
            fit="contain"
          />
          <Text fw={700} size="lg" ta="center">
            {t("nav.company_portal_of") + " "}
            <Anchor
              href={serverData.visWebsiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              fw={700}
              td="underline"
            >
              {t("nav.vis_short")}
            </Anchor>
          </Text>
        </Group>
        <Divider my="xs" label={t("nav.navigation")} labelPosition="center" />
        <Stack gap="xs">
          <Button
            component={NavLink}
            to="/"
            leftSection={<IconHome2 />}
            variant="subtle"
            justify="flex-start"
          >
            {t("nav.home")}
          </Button>
          {user?.email_confirmed && user.user_confirmed && user.company_id && (
            <>
              <Button
                component={NavLink}
                to="/profile"
                leftSection={<IconUser />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.profile")}
              </Button>
              <Button
                component={NavLink}
                to="/company"
                leftSection={<IconBuilding />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.company")}
              </Button>
              <Button
                component={NavLink}
                to="/kp"
                leftSection={<IconCalendarEvent />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.kontaktparty")}
              </Button>
            </>
          )}
          {(user?.is_staff || user?.is_admin) && (
            <>
              <Button
                component={NavLink}
                to="/user-management"
                leftSection={<IconSettings />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.user_management")}
              </Button>
              <Button
                component={NavLink}
                to="/company-management"
                leftSection={<IconBuilding />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.company_management")}
              </Button>
            </>
          )}
          <Button
            onClick={() => {
              logout();
            }}
            leftSection={<IconLogout2 />}
            color="red"
            variant="light"
            justify="flex-start"
          >
            {t("nav.logout")}
          </Button>
        </Stack>
      </Stack>
    </AppShell.Navbar>
  );
}
