import {
  Center,
  Stack,
  Title,
  Loader,
  Alert,
  Button,
  Tabs,
} from "@mantine/core";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  useConfirmUser,
  useGetAllAdmins,
  useGetAllCompanies,
  useGetAllStaff,
  useGetUnconfirmedUsers,
} from "../orval/generated/user/user";
import { isStaff } from "../api/utils";

import UserTable from "../components/UserTable";
import type {
  CompanyUserResponse,
  User,
} from "../orval/generated/fastAPI.schemas";
import NotAllowed from "../components/NotAllowed";

export default function UserManagement() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string | null>("unconfirmed");

  const {
    data: unconfirmedUsers,
    isLoading: isUnconfirmedLoading,
    isError: isUnconfirmedError,
  } = useGetUnconfirmedUsers({
    query: { enabled: activeTab === "unconfirmed" },
  });
  const {
    data: staffUsers,
    isLoading: isStaffLoading,
    isError: isStaffError,
  } = useGetAllStaff({ query: { enabled: activeTab === "staff" } });
  const {
    data: companyUsers,
    isLoading: isCompaniesLoading,
    isError: isCompaniesError,
  } = useGetAllCompanies({ query: { enabled: activeTab === "companies" } });
  const {
    data: adminUsers,
    isLoading: isAdminsLoading,
    isError: isAdminsError,
  } = useGetAllAdmins({ query: { enabled: activeTab === "admins" } });

  const staffStatus = isStaff();

  const {
    mutate: confirm,
    isPending: isConfirming,
    isError: isConfirmError,
  } = useConfirmUser({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["/user/unconfirmed"] });
      },
    },
  });

  const handleConfirmUser = (userId: string | undefined) => {
    if (!userId) return;
    confirm({ userId });
  };

  if (!staffStatus) {
    return <NotAllowed />;
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1000} gap="lg">
        <Title order={2}>{t("user_management.title")}</Title>

        {isConfirmError && (
          <Alert
            icon={<IconAlertCircle />}
            color="red"
            title={t("server.error")}
          >
            {t("user_management.confirm_error")}
          </Alert>
        )}

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="unconfirmed">
              {t("user_management.tabs.unconfirmed")}
            </Tabs.Tab>
            <Tabs.Tab value="staff">{t("user_management.tabs.staff")}</Tabs.Tab>
            <Tabs.Tab value="companies">
              {t("user_management.tabs.companies")}
            </Tabs.Tab>
            <Tabs.Tab value="admins">
              {t("user_management.tabs.admins")}
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="unconfirmed" pt="md">
            {isUnconfirmedLoading ? (
              <Center py="xl">
                <Loader />
              </Center>
            ) : isUnconfirmedError ? (
              <Alert
                icon={<IconAlertCircle />}
                color="red"
                title={t("server.error")}
              >
                {t("user_management.error")}
              </Alert>
            ) : unconfirmedUsers && unconfirmedUsers.length > 0 ? (
              <UserTable
                users={unconfirmedUsers as CompanyUserResponse[]}
                t={t}
                actionButton={(user) => (
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<IconCheck size={14} />}
                    onClick={() => handleConfirmUser(user.id)}
                    disabled={isConfirming || !user.id}
                    loading={isConfirming}
                  >
                    {t("user_management.confirm")}
                  </Button>
                )}
              />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_users")}
              >
                {t("user_management.no_users_description")}
              </Alert>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="staff" pt="md">
            {isStaffLoading ? (
              <Center py="xl">
                <Loader />
              </Center>
            ) : isStaffError ? (
              <Alert
                icon={<IconAlertCircle />}
                color="red"
                title={t("server.error")}
              >
                {t("user_management.error")}
              </Alert>
            ) : staffUsers && staffUsers.length > 0 ? (
              <UserTable
                users={staffUsers as User[]}
                t={t}
                showCompany={false}
              />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_staff")}
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="companies" pt="md">
            {isCompaniesLoading ? (
              <Center py="xl">
                <Loader />
              </Center>
            ) : isCompaniesError ? (
              <Alert
                icon={<IconAlertCircle />}
                color="red"
                title={t("server.error")}
              >
                {t("user_management.error")}
              </Alert>
            ) : companyUsers && companyUsers.length > 0 ? (
              <UserTable users={companyUsers as unknown as User[]} t={t} />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_companies")}
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="admins" pt="md">
            {isAdminsLoading ? (
              <Center py="xl">
                <Loader />
              </Center>
            ) : isAdminsError ? (
              <Alert
                icon={<IconAlertCircle />}
                color="red"
                title={t("server.error")}
              >
                {t("user_management.error")}
              </Alert>
            ) : adminUsers && adminUsers.length > 0 ? (
              <UserTable
                users={adminUsers as User[]}
                t={t}
                showCompany={false}
              />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_admins")}
              />
            )}
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Center>
  );
}
