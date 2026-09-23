import {
  Anchor,
  AppShell,
  Button,
  Divider,
  Group,
  Image,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconBuilding,
  IconCalendarEvent,
  IconBuildingFactory2,
  IconHome2,
  IconLogout2,
  IconMail,
  IconSettings,
  IconUser,
} from "@tabler/icons-react";
import { useState } from "react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { clearAuthState } from "../api/utils";
import { useLogoutUser } from "../orval/generated/user/user";
import { useCurrentUser } from "../context/useCurrentUser";
import serverData from "../utils/server-data";

const Navbar = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const [isLogoutConfirmOpen, setIsLogoutConfirmOpen] = useState(false);

  const { mutate: logout, isPending: isLoggingOut } = useLogoutUser({
    mutation: {
      onSettled: () => {
        clearAuthState();
        queryClient.clear();
        navigate("/login");
      },
    },
  });

  return (
    <AppShell.Navbar p="md" className="app-navbar">
      <Modal
        centered
        opened={isLogoutConfirmOpen}
        onClose={() => setIsLogoutConfirmOpen(false)}
        title={t("nav.logout_confirm_title")}
      >
        <Stack gap="md">
          <Text size="sm">{t("nav.logout_confirm_body")}</Text>
          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => setIsLogoutConfirmOpen(false)}
            >
              {t("common.cancel")}
            </Button>
            <Button
              color="red"
              loading={isLoggingOut}
              onClick={() => {
                logout();
              }}
            >
              {t("nav.logout_confirm_submit")}
            </Button>
          </Group>
        </Stack>
      </Modal>
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
            {`${t("nav.company_portal_of")} `}
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
          {user && (user.is_staff || user.is_admin) && (
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
              <Button
                component={NavLink}
                to="/admin/mail-templates"
                leftSection={<IconMail />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.mail_templates")}
              </Button>
              <Button
                component={NavLink}
                to="/admin/industries"
                leftSection={<IconBuildingFactory2 />}
                variant="subtle"
                justify="flex-start"
              >
                {t("nav.industries")}
              </Button>
            </>
          )}
          <Button
            onClick={() => setIsLogoutConfirmOpen(true)}
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
};
export default Navbar;
