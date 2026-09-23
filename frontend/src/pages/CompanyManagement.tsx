import {
  ActionIcon,
  Alert,
  Center,
  Group,
  Loader,
  Pagination,
  Paper,
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
  IconId,
  IconPencil,
  IconSearch,
  IconTrash,
  IconUsers,
  IconX,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import CompanyDeleteModal from "../components/admin/CompanyDeleteModal";
import CompanyMembersDrawer from "../components/admin/CompanyMembersDrawer";
import { useCurrentUser } from "../context/useCurrentUser";
import {
  getSearchCompaniesQueryKey,
  useSearchCompanies,
  useUpdateCompany,
} from "../orval/generated/company/company";
import type { CompanyListResult } from "../orval/generated/fastAPI.schemas";

const SEARCH_DEBOUNCE_MS = 300;
const PAGE_SIZE = 25;

const CompanyManagement = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const isAdmin = user?.is_admin ?? false;

  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);
  const [page, setPage] = useState(1);
  const [renamedId, setRenamedId] = useState<string | null>(null);
  const [renamedName, setRenamedName] = useState("");
  const [membersCompany, setMembersCompany] =
    useState<CompanyListResult | null>(null);
  const [deletedCompany, setDeletedCompany] =
    useState<CompanyListResult | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const { data, isLoading, isError } = useSearchCompanies({
    query: debouncedSearch.trim() || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  const { mutate: rename, isPending: isRenaming } = useUpdateCompany({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getSearchCompaniesQueryKey(),
        });
        setRenamedId(null);
        notifications.show({
          color: "green",
          message: t("company_management.renamed"),
        });
      },
    },
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1200} gap="lg">
        <Title order={2}>{t("company_management.title")}</Title>

        <CompanyMembersDrawer
          company={membersCompany}
          onClose={() => setMembersCompany(null)}
        />
        <CompanyDeleteModal
          company={
            deletedCompany
              ? {
                  id: deletedCompany.id,
                  name: deletedCompany.name,
                  usersCount: deletedCompany.users_count,
                }
              : null
          }
          onClose={() => setDeletedCompany(null)}
        />

        <TextInput
          leftSection={<IconSearch size={16} />}
          maw={360}
          onChange={(event) => setSearch(event.currentTarget.value)}
          placeholder={t("company_management.search_placeholder")}
          value={search}
        />

        {isError ? (
          <Alert
            color="red"
            icon={<IconAlertCircle />}
            title={t("server.error")}
          >
            {t("company_management.error")}
          </Alert>
        ) : (
          <Paper withBorder p="lg" radius="md">
            {isLoading ? (
              <Center py="md">
                <Loader />
              </Center>
            ) : items.length === 0 ? (
              <Text c="dimmed">
                {t("company_management.no_companies_description")}
              </Text>
            ) : (
              <>
                <Table.ScrollContainer minWidth={700}>
                  <Table highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>
                          {t("company_management.company_name")}
                        </Table.Th>
                        <Table.Th>
                          {t("company_management.users_count")}
                        </Table.Th>
                        <Table.Th>
                          {t("company_management.bookings_count")}
                        </Table.Th>
                        <Table.Th>{t("company_management.actions")}</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {items.map((company) => (
                        <Table.Tr key={company.id}>
                          <Table.Td>
                            {renamedId === company.id ? (
                              <Group gap="xs" wrap="nowrap">
                                <TextInput
                                  aria-label={t("company_management.rename")}
                                  disabled={isRenaming}
                                  onChange={(event) =>
                                    setRenamedName(event.currentTarget.value)
                                  }
                                  value={renamedName}
                                />
                                <ActionIcon
                                  aria-label={t(
                                    "company_management.rename_save",
                                  )}
                                  color="green"
                                  disabled={
                                    isRenaming || renamedName.trim() === ""
                                  }
                                  onClick={() =>
                                    rename({
                                      companyId: company.id,
                                      data: { name: renamedName.trim() },
                                    })
                                  }
                                  variant="light"
                                >
                                  <IconCheck size={16} />
                                </ActionIcon>
                                <ActionIcon
                                  aria-label={t(
                                    "company_management.rename_cancel",
                                  )}
                                  disabled={isRenaming}
                                  onClick={() => setRenamedId(null)}
                                  variant="subtle"
                                >
                                  <IconX size={16} />
                                </ActionIcon>
                              </Group>
                            ) : (
                              <Group gap="xs" wrap="nowrap">
                                <Text>{company.name}</Text>
                                <ActionIcon
                                  aria-label={t("company_management.rename")}
                                  onClick={() => {
                                    setRenamedId(company.id);
                                    setRenamedName(company.name);
                                  }}
                                  variant="subtle"
                                >
                                  <IconPencil size={16} />
                                </ActionIcon>
                              </Group>
                            )}
                          </Table.Td>
                          <Table.Td>{company.users_count}</Table.Td>
                          <Table.Td>{company.bookings_count}</Table.Td>
                          <Table.Td>
                            <Group gap="xs" wrap="nowrap">
                              <Tooltip
                                label={t("company_management.view_users")}
                                withArrow
                              >
                                <ActionIcon
                                  aria-label={t(
                                    "company_management.view_users",
                                  )}
                                  onClick={() => setMembersCompany(company)}
                                  variant="light"
                                >
                                  <IconUsers size={16} />
                                </ActionIcon>
                              </Tooltip>
                              <Tooltip
                                label={t("company_management.edit_profile")}
                                withArrow
                              >
                                <ActionIcon
                                  aria-label={t(
                                    "company_management.edit_profile",
                                  )}
                                  onClick={() =>
                                    navigate(
                                      `/company-management/${company.id}/profile`,
                                    )
                                  }
                                  variant="light"
                                >
                                  <IconId size={16} />
                                </ActionIcon>
                              </Tooltip>
                              {isAdmin ? (
                                <Tooltip
                                  label={t("company_management.delete")}
                                  withArrow
                                >
                                  <ActionIcon
                                    aria-label={t("company_management.delete")}
                                    color="red"
                                    onClick={() => setDeletedCompany(company)}
                                    variant="light"
                                  >
                                    <IconTrash size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              ) : null}
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>

                <Group justify="space-between" mt="sm">
                  <Text c="dimmed" size="sm">
                    {t("company_management.total", { total })}
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

export default CompanyManagement;
