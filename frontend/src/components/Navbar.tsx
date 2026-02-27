import { AppShell, Button, Divider, Group, Stack, Text } from "@mantine/core";
import {
  IconBuilding,
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
            {t("nav.home")}
          </Button>
          {user?.email_confirmed && user.user_confirmed && user.is_company && (
            <Button
              component={NavLink}
              to="/profile"
              leftSection={<IconUser />}
            >
              {t("nav.profile")}
            </Button>
          )}
          {(user?.is_staff || user?.is_admin) && (
            <>
              <Button
                component={NavLink}
                to="/user-management"
                leftSection={<IconSettings />}
              >
                {t("nav.user_management")}
              </Button>
              <Button
                component={NavLink}
                to="/company-management"
                leftSection={<IconBuilding />}
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
          >
            {t("nav.logout")}
          </Button>
        </Stack>
      </Stack>
    </AppShell.Navbar>
  );
}
