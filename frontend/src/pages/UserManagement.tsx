import {
  Center,
  Stack,
  Title,
  Loader,
  Alert,
  Button,
  Tabs,
  Modal,
  Text,
  Group,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconTrash,
  IconUserSearch,
} from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  getGetAllCompanyUsersQueryKey,
  getGetCurrentUserQueryKey,
  getGetUnconfirmedUsersQueryKey,
  useConfirmUser,
  useDeleteUser,
  useGetAllAdmins,
  useGetAllCompanyUsers,
  useGetAllStaff,
  useGetUnconfirmedUsers,
} from "../orval/generated/user/user";
import {
  isImpersonating,
  setImpersonation,
  getImpersonatingUserId,
} from "../api/utils";

import UserTable from "../components/UserTable";
import type { UserResponse } from "../orval/generated/fastAPI.schemas";
import { useCurrentUser } from "../context/useCurrentUser";
import { useNavigate } from "react-router";

const UserManagement = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const navigate = useNavigate();
  const adminStatus = user?.is_admin ?? false;
  const [activeTab, setActiveTab] = useState<string | null>("unconfirmed");
  const [deleteModalOpened, setDeleteModalOpened] = useState(false);
  const [userToDelete, setUserToDelete] = useState<UserResponse | null>(null);

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
  } = useGetAllCompanyUsers({ query: { enabled: activeTab === "companies" } });
  const {
    data: adminUsers,
    isLoading: isAdminsLoading,
    isError: isAdminsError,
  } = useGetAllAdmins({ query: { enabled: activeTab === "admins" } });

  const {
    mutate: confirm,
    isPending: isConfirming,
    isError: isConfirmError,
  } = useConfirmUser({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: getGetUnconfirmedUsersQueryKey(),
        });
      },
    },
  });

  const {
    mutate: deleteUser,
    isPending: isDeleting,
    isError: isDeleteError,
  } = useDeleteUser({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: getGetAllCompanyUsersQueryKey(),
        });
        setDeleteModalOpened(false);
      },
    },
  });

  const handleConfirmUser = (userId: string | undefined) => {
    if (!userId) return;
    confirm({ userId });
  };

  const handleImpersonateUser = (
    userId: string | undefined,
    displayName: string,
  ) => {
    if (!adminStatus || !userId) return;
    setImpersonation(userId, displayName);
    navigate("/", { replace: true });
  };

  const handleDeleteUser = (userId: string | undefined) => {
    if (!adminStatus) return;
    if (!userId) return;
    const targetUser = companyUsers?.find((user) => user.id === userId);
    if (!targetUser) return;
    setUserToDelete(targetUser as UserResponse);
    setDeleteModalOpened(true);
  };

  const confirmDeleteUser = () => {
    if (!adminStatus) return;
    if (!userToDelete?.id) return;
    deleteUser({ userId: userToDelete.id });
  };

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1000} gap="lg">
        <Title order={2}>{t("user_management.title")}</Title>

        <Modal
          opened={adminStatus && deleteModalOpened}
          onClose={() => {
            if (!isDeleting) {
              setDeleteModalOpened(false);
            }
          }}
          onExitTransitionEnd={() => {
            if (!deleteModalOpened) {
              setUserToDelete(null);
            }
          }}
          closeOnClickOutside={!isDeleting}
          closeOnEscape={!isDeleting}
          withCloseButton={!isDeleting}
          title={t("user_management.delete_modal.title")}
          centered
        >
          <Stack gap="sm">
            <Text>
              {t("user_management.delete_modal.message", {
                email: userToDelete?.email ?? "-",
              })}
            </Text>
            <Text c="red" fw={600}>
              {t("user_management.delete_modal.irreversible")}
            </Text>
            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => setDeleteModalOpened(false)}
                disabled={isDeleting}
              >
                {t("user_management.delete_modal.cancel")}
              </Button>
              <Button
                color="red"
                onClick={confirmDeleteUser}
                loading={isDeleting}
                disabled={!userToDelete?.id}
              >
                {t("user_management.delete_modal.confirm")}
              </Button>
            </Group>
          </Stack>
        </Modal>

        {isConfirmError && (
          <Alert
            icon={<IconAlertCircle />}
            color="red"
            title={t("server.error")}
          >
            {t("user_management.confirm_error")}
          </Alert>
        )}

        {adminStatus && isDeleteError && (
          <Alert
            icon={<IconAlertCircle />}
            color="red"
            title={t("server.error")}
          >
            {t("user_management.delete_error")}
          </Alert>
        )}

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="unconfirmed">
              {t("user_management.tabs.unconfirmed")}
            </Tabs.Tab>
            <Tabs.Tab value="companies">
              {t("user_management.tabs.companies")}
            </Tabs.Tab>
            <Tabs.Tab value="staff">{t("user_management.tabs.staff")}</Tabs.Tab>
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
                users={unconfirmedUsers}
                t={t}
                actionButton={(user) => (
                  <Button
                    size="xs"
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
              <UserTable
                users={companyUsers}
                t={t}
                actionButton={
                  adminStatus
                    ? (user) => {
                        const displayName =
                          user.first_name || user.last_name
                            ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
                            : user.email;
                        const isCurrentlyImpersonating =
                          isImpersonating() &&
                          getImpersonatingUserId() === user.id;
                        return (
                          <Group gap="xs" wrap="nowrap">
                            <Button
                              leftSection={<IconUserSearch size={14} />}
                              size="xs"
                              color="blue"
                              variant="light"
                              onClick={() =>
                                handleImpersonateUser(user.id, displayName)
                              }
                              disabled={!user.id || isCurrentlyImpersonating}
                            >
                              {isCurrentlyImpersonating
                                ? t("user_management.impersonating")
                                : t("user_management.impersonate")}
                            </Button>
                            <Button
                              leftSection={<IconTrash size={14} />}
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => handleDeleteUser(user.id)}
                              disabled={!user.id}
                            >
                              {t("user_management.delete")}
                            </Button>
                          </Group>
                        );
                      }
                    : undefined
                }
              />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_companies")}
              />
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
              <UserTable users={staffUsers} t={t} showCompany={false} />
            ) : (
              <Alert
                icon={<IconAlertCircle />}
                color="blue"
                title={t("user_management.no_staff")}
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
              <UserTable users={adminUsers} t={t} showCompany={false} />
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
};
export default UserManagement;
