import {
  ActionIcon,
  Badge,
  Center,
  CloseButton,
  Group,
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
import { notifySuccess } from "../utils/notify";
import {
  IconMailForward,
  IconPencil,
  IconSearch,
  IconTrash,
  IconUserSearch,
} from "@tabler/icons-react";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import UserDeleteModal from "../components/admin/UserDeleteModal";
import UserEditDrawer from "../components/admin/UserEditDrawer";
import UserFlagBadges from "../components/admin/UserFlagBadges";
import { useImpersonate } from "../components/admin/useImpersonate";
import { useCurrentUser } from "../context/useCurrentUser";
import SortableHeader from "../components/SortableHeader";
import {
  UserFilter,
  type UserResponse,
  type UserSort,
} from "../orval/generated/fastAPI.schemas";
import {
  useListUsers,
  useResendUserConfirmationMail,
} from "../orval/generated/user/user";
import { useGetCompanyWithUsers } from "../orval/generated/company/company";
import { getDisplayName } from "../utils/display";
import { useSort } from "../utils/sort";
import BookingNewAdditionsBadge from "../components/staff-bookings/BookingNewAdditionsBadge";
import { formatDate, formatDateTime } from "../utils/date-format";
import PageLoader from "../components/PageLoader";
import ErrorAlert from "../components/ErrorAlert";

const SEARCH_DEBOUNCE_MS = 300;
const PAGE_SIZE = 25;

const SORT_COLUMNS: [UserSort, string][] = [
  ["email", "user_management.email"],
  ["name", "user_management.name"],
  ["company", "user_management.company"],
  ["role", "user_management.flags.header"],
  ["status", "user_management.status"],
  ["signed_up", "user_management.signed_up"],
  ["last_login", "user_management.last_login"],
];

const filterLabelKeys: Record<UserFilter, string> = {
  [UserFilter.all]: "user_management.filters.all",
  [UserFilter.company]: "user_management.filters.company",
  [UserFilter.staff]: "user_management.filters.staff",
  [UserFilter.new]: "user_management.filters.new",
};

const isUserFilter = (value: string | null): value is UserFilter =>
  value !== null && value in filterLabelKeys;

const UserManagement = () => {
  const { t } = useTranslation();
  const { user: currentUser } = useCurrentUser();
  const isAdmin = currentUser?.is_admin ?? false;
  const { canImpersonate, canImpersonateUser, impersonate } = useImpersonate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [search, setSearch] = useState(() => searchParams.get("query") ?? "");
  const [debouncedSearch] = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);
  const [filter, setFilter] = useState<UserFilter>(() => {
    const initial = searchParams.get("filter");
    return isUserFilter(initial) ? initial : UserFilter.all;
  });
  const [companyId, setCompanyId] = useState<string | null>(() =>
    searchParams.get("company"),
  );
  const [page, setPage] = useState(1);
  const { sort, toggleSort } = useSort<UserSort>(null, () => setPage(1));
  const [editedUser, setEditedUser] = useState<UserResponse | null>(null);
  const [deletedUser, setDeletedUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filter, companyId]);

  useEffect(() => {
    const query = debouncedSearch.trim();
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (query) next.set("query", query);
        else next.delete("query");
        if (filter === UserFilter.all) next.delete("filter");
        else next.set("filter", filter);
        if (companyId) next.set("company", companyId);
        else next.delete("company");
        return next;
      },
      { replace: true },
    );
  }, [companyId, debouncedSearch, filter, setSearchParams]);

  const { data, isLoading, isError } = useListUsers(
    {
      query: debouncedSearch.trim() || undefined,
      filter,
      page,
      page_size: PAGE_SIZE,
      sort: sort?.field,
      direction: sort?.direction,
      company: companyId ?? undefined,
    },
    { query: { placeholderData: keepPreviousData } },
  );
  const { data: filterCompany } = useGetCompanyWithUsers(companyId ?? "", {
    query: { enabled: companyId !== null },
  });

  const { mutate: resendConfirmation, isPending: isResending } =
    useResendUserConfirmationMail({
      mutation: {
        onSuccess: () => {
          notifySuccess(t("user_management.resent_notice"));
        },
      },
    });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (data && page > totalPages) setPage(totalPages);
  }, [data, page, totalPages]);

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

        {companyId ? (
          <Group>
            <Badge
              rightSection={
                <CloseButton
                  aria-label={t("user_management.clear_company_filter")}
                  onClick={() => setCompanyId(null)}
                  size="xs"
                />
              }
              size="lg"
              tt="none"
              variant="light"
            >
              {t("user_management.company_filter", {
                company: filterCompany?.name ?? companyId,
              })}
            </Badge>
          </Group>
        ) : null}

        {isError ? (
          <ErrorAlert>{t("user_management.error")}</ErrorAlert>
        ) : (
          <Paper withBorder p="lg" radius="md">
            {isLoading ? (
              <PageLoader />
            ) : (
              <>
                {items.length === 0 ? (
                  <Text c="dimmed">{t("user_management.table_empty")}</Text>
                ) : (
                  <Table.ScrollContainer minWidth={1100}>
                    <Table highlightOnHover>
                      <Table.Thead>
                        <Table.Tr>
                          {SORT_COLUMNS.map(([field, labelKey]) => (
                            <SortableHeader
                              key={field}
                              field={field}
                              label={t(labelKey)}
                              sort={sort}
                              onSort={toggleSort}
                            />
                          ))}
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
                            <Table.Td>
                              <Group gap="xs" wrap="nowrap">
                                {item.company?.name ?? "-"}
                                {item.new_in_company_since ? (
                                  <BookingNewAdditionsBadge />
                                ) : null}
                              </Group>
                            </Table.Td>
                            <Table.Td>
                              <UserFlagBadges user={item} />
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs" wrap="wrap">
                                {item.email_confirmed ? (
                                  <Badge color="green" variant="light">
                                    {t("user_management.confirmed")}
                                  </Badge>
                                ) : (
                                  <Badge color="orange" variant="light">
                                    {t("user_management.email_unconfirmed")}
                                  </Badge>
                                )}
                                {item.pending_email ? (
                                  <Tooltip label={item.pending_email} withArrow>
                                    <Badge color="blue" variant="light">
                                      {t(
                                        "user_management.email_change_pending",
                                      )}
                                    </Badge>
                                  </Tooltip>
                                ) : null}
                              </Group>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm" style={{ whiteSpace: "nowrap" }}>
                                {formatDate(item.created_at) ?? "-"}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              {item.last_login_at ? (
                                <Text
                                  size="sm"
                                  style={{ whiteSpace: "nowrap" }}
                                >
                                  {formatDateTime(item.last_login_at)}
                                </Text>
                              ) : (
                                <Text size="sm" c="dimmed">
                                  {t("user_management.never_logged_in")}
                                </Text>
                              )}
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs" wrap="nowrap">
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
                                {canImpersonate ? (
                                  <Tooltip
                                    label={t("user_management.impersonate")}
                                    withArrow
                                  >
                                    <ActionIcon
                                      aria-label={t(
                                        "user_management.impersonate",
                                      )}
                                      color="blue"
                                      disabled={!canImpersonateUser(item)}
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
                )}

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
