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
import { useEffect, useState } from "react";
import { clearToken, isCompany, isStaff } from "../api/utils";
import { useLogoutUser } from "../orval/generated/user/user";

export default function Navbar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [staffStatus, setStaffStatus] = useState(false);
  const [companyStatus, setCompanyStatus] = useState(false);

  const { mutate: logout } = useLogoutUser({
    mutation: {
      onSuccess: () => {
        navigate("/login");
        clearToken();
      },
    },
  });

  // Listen for changes in authentication token to update staff status
  // Otherwise the navbar won't update after login/logout until a page refresh
  useEffect(() => {
    const updateRoleStatus = () => {
      try {
        setStaffStatus(isStaff());
        setCompanyStatus(isCompany());
      } catch {
        setStaffStatus(false);
        setCompanyStatus(false);
      }
    };

    updateRoleStatus();
    window.addEventListener("auth-token-changed", updateRoleStatus);
    return () =>
      window.removeEventListener("auth-token-changed", updateRoleStatus);
  }, []);

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
          {companyStatus && (
            <Button
              component={NavLink}
              to="/profile"
              leftSection={<IconUser />}
            >
              {t("nav.profile")}
            </Button>
          )}
          {staffStatus && (
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
