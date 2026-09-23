import {
  ActionIcon,
  Alert,
  Badge,
  Center,
  Group,
  Loader,
  Pagination,
  Paper,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconMailForward,
  IconPencil,
  IconSearch,
  IconTrash,
  IconUserSearch,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { resetQueriesForIdentityChange } from "../api/query-cache";
import { getImpersonatingUserId, setImpersonation } from "../api/utils";
import UserDeleteModal from "../components/admin/UserDeleteModal";
import UserEditDrawer from "../components/admin/UserEditDrawer";
import UserFlagBadges from "../components/admin/UserFlagBadges";
import { useCurrentUser } from "../context/useCurrentUser";
import {
  UserFilter,
  type UserResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getListUsersQueryKey,
  useConfirmUser,
  useListUsers,
  useResendUserConfirmationMail,
} from "../orval/generated/user/user";
import { getDisplayName } from "../utils/display";

const SEARCH_DEBOUNCE_MS = 300;
const PAGE_SIZE = 25;

const filterLabelKeys: Record<UserFilter, string> = {
  [UserFilter.all]: "user_management.filters.all",
  [UserFilter.unconfirmed]: "user_management.filters.unconfirmed",
  [UserFilter.company]: "user_management.filters.company",
  [UserFilter.staff]: "user_management.filters.staff",
};

const UserManagement = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user: currentUser } = useCurrentUser();
  const isAdmin = currentUser?.is_admin ?? false;

  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);
  const [filter, setFilter] = useState<UserFilter>(UserFilter.all);
  const [page, setPage] = useState(1);
  const [editedUser, setEditedUser] = useState<UserResponse | null>(null);
  const [deletedUser, setDeletedUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filter]);

  const { data, isLoading, isError } = useListUsers({
    query: debouncedSearch.trim() || undefined,
    filter,
    page,
    page_size: PAGE_SIZE,
  });

  const invalidateUsers = () =>
    queryClient.invalidateQueries({ queryKey: getListUsersQueryKey() });

  const { mutate: confirmUser, isPending: isConfirming } = useConfirmUser({
    mutation: {
      onSuccess: async () => {
        await invalidateUsers();
        notifications.show({
          color: "green",
          message: t("user_management.confirmed_notice"),
        });
      },
    },
  });

  const { mutate: resendConfirmation, isPending: isResending } =
    useResendUserConfirmationMail({
      mutation: {
        onSuccess: () => {
          notifications.show({
            color: "green",
            message: t("user_management.resent_notice"),
          });
        },
      },
    });

  const impersonate = (target: UserResponse) => {
    if (!isAdmin) return;
    setImpersonation(
      target.id,
      getDisplayName(target.first_name, target.last_name, target.email),
    );
    resetQueriesForIdentityChange(queryClient);
    navigate("/", { replace: true });
  };

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1200} gap="lg">
        <Title order={2}>{t("user_management.title")}</Title>

        <UserEditDrawer
          canEditPrivileges={isAdmin}
          onClose={() => setEditedUser(null)}
          user={editedUser}
        />
        <UserDeleteModal
          onClose={() => setDeletedUser(null)}
          user={deletedUser}
        />

        <Group align="flex-end" gap="sm" justify="space-between">
          <TextInput
            flex={1}
            leftSection={<IconSearch size={16} />}
            maw={360}
            onChange={(event) => setSearch(event.currentTarget.value)}
            placeholder={t("user_management.search_placeholder")}
            value={search}
          />
          <SegmentedControl
            data={Object.entries(filterLabelKeys).map(([value, labelKey]) => ({
              value,
              label: t(labelKey),
            }))}
            onChange={(value) => setFilter(value as UserFilter)}
            value={filter}
          />
        </Group>

        {isError ? (
          <Alert
            color="red"
            icon={<IconAlertCircle />}
            title={t("server.error")}
          >
            {t("user_management.error")}
          </Alert>
        ) : (
          <Paper withBorder p="lg" radius="md">
            {isLoading ? (
              <Center py="md">
                <Loader />
              </Center>
            ) : items.length === 0 ? (
              <Text c="dimmed">{t("user_management.table_empty")}</Text>
            ) : (
              <>
                <Table.ScrollContainer minWidth={900}>
                  <Table highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>{t("user_management.email")}</Table.Th>
                        <Table.Th>{t("user_management.name")}</Table.Th>
                        <Table.Th>{t("user_management.company")}</Table.Th>
                        <Table.Th>{t("user_management.flags.header")}</Table.Th>
                        <Table.Th>{t("user_management.status")}</Table.Th>
                        <Table.Th>{t("user_management.actions")}</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {items.map((item) => (
                        <Table.Tr key={item.id}>
                          <Table.Td>{item.email}</Table.Td>
                          <Table.Td>
                            {getDisplayName(item.first_name, item.last_name)}
                          </Table.Td>
                          <Table.Td>{item.company?.name ?? "-"}</Table.Td>
                          <Table.Td>
                            <UserFlagBadges user={item} />
                          </Table.Td>
                          <Table.Td>
                            <Group gap="xs" wrap="wrap">
                              <Badge
                                color={item.user_confirmed ? "green" : "yellow"}
                                variant="light"
                              >
                                {item.user_confirmed
                                  ? t("user_management.confirmed")
                                  : t("user_management.unconfirmed")}
                              </Badge>
                              {item.email_confirmed ? null : (
                                <Badge color="orange" variant="light">
                                  {t("user_management.email_unconfirmed")}
                                </Badge>
                              )}
                            </Group>
                          </Table.Td>
                          <Table.Td>
                            <Group gap="xs" wrap="nowrap">
                              {item.user_confirmed ? null : (
                                <Tooltip
                                  label={t("user_management.confirm")}
                                  withArrow
                                >
                                  <ActionIcon
                                    aria-label={t("user_management.confirm")}
                                    color="green"
                                    disabled={isConfirming}
                                    onClick={() =>
                                      confirmUser({ userId: item.id })
                                    }
                                    variant="light"
                                  >
                                    <IconCheck size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              )}
                              {item.email_confirmed ? null : (
                                <Tooltip
                                  label={t("user_management.resend")}
                                  withArrow
                                >
                                  <ActionIcon
                                    aria-label={t("user_management.resend")}
                                    disabled={isResending}
                                    onClick={() =>
                                      resendConfirmation({ userId: item.id })
                                    }
                                    variant="light"
                                  >
                                    <IconMailForward size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              )}
                              {isAdmin ? (
                                <Tooltip
                                  label={t("user_management.impersonate")}
                                  withArrow
                                >
                                  <ActionIcon
                                    aria-label={t(
                                      "user_management.impersonate",
                                    )}
                                    color="blue"
                                    disabled={
                                      getImpersonatingUserId() === item.id
                                    }
                                    onClick={() => impersonate(item)}
                                    variant="light"
                                  >
                                    <IconUserSearch size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              ) : null}
                              <Tooltip
                                label={t("user_management.edit.title")}
                                withArrow
                              >
                                <ActionIcon
                                  aria-label={t("user_management.edit.title")}
                                  onClick={() => setEditedUser(item)}
                                  variant="light"
                                >
                                  <IconPencil size={16} />
                                </ActionIcon>
                              </Tooltip>
                              <Tooltip
                                label={t("user_management.delete")}
                                withArrow
                              >
                                <ActionIcon
                                  aria-label={t("user_management.delete")}
                                  color="red"
                                  onClick={() => setDeletedUser(item)}
                                  variant="light"
                                >
                                  <IconTrash size={16} />
                                </ActionIcon>
                              </Tooltip>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>

                <Group justify="space-between" mt="sm">
                  <Text c="dimmed" size="sm">
                    {t("user_management.total", { total })}
                  </Text>
                  <Pagination
                    onChange={setPage}
                    total={totalPages}
                    value={page}
                    withEdges
                  />
                </Group>
              </>
            )}
          </Paper>
        )}
      </Stack>
    </Center>
  );
};

export default UserManagement;
