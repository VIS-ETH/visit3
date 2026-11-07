import {
  Center,
  Group,
  Pagination,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { getApiErrorStatus } from "../api/errors";
import CompanyBookingActions from "../components/admin/CompanyBookingActions";
import CompanyDeleteModal from "../components/admin/CompanyDeleteModal";
import CompanyMembersDrawer from "../components/admin/CompanyMembersDrawer";
import CompanyFilters from "../components/company-management/CompanyFilters";
import CompanyNameCell from "../components/company-management/CompanyNameCell";
import CompanyRowActions from "../components/company-management/CompanyRowActions";
import { useCompanyBookingEvent } from "../components/company-management/use-company-booking-event";
import { useCompanyListParams } from "../components/company-management/use-company-list-params";
import { useSearchPage } from "../components/company-management/use-search-page";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import SortableHeader from "../components/SortableHeader";
import { useCurrentUser } from "../context/useCurrentUser";
import { useAsyncAction } from "../hooks/use-async-action";
import {
  confirmCompany,
  getSearchCompaniesQueryKey,
  updateCompany,
  useSearchCompanies,
} from "../orval/generated/company/company";
import type {
  CompanyListResult,
  CompanySort,
} from "../orval/generated/fastAPI.schemas";
import { notifyError, notifySuccess } from "../utils/notify";
import { useSort } from "../utils/sort";

const SEARCH_DEBOUNCE_MS = 300;
const PAGE_SIZE = 25;
const CONFLICT = 409;

const CompanyManagement = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const isAdmin = user?.is_admin ?? false;
  const canMail = user?.is_kp_president ?? false;

  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);
  const [page, setPage] = useSearchPage(debouncedSearch);
  const { filter, setFilter, companyId, clearCompany } = useCompanyListParams(
    () => setPage(1),
  );
  const { sort, toggleSort } = useSort<CompanySort>(
    { field: "name", direction: "asc" },
    () => setPage(1),
  );
  const [renamedId, setRenamedId] = useState<string | null>(null);
  const [membersCompany, setMembersCompany] =
    useState<CompanyListResult | null>(null);
  const [deletedCompany, setDeletedCompany] =
    useState<CompanyListResult | null>(null);

  const {
    events,
    isLoadingEvents,
    bookingEvent,
    pickEvent,
    activeBookingByCompanyId,
  } = useCompanyBookingEvent();

  const mailCompany = (companyId: string) => {
    const params = new URLSearchParams({ company: companyId });
    if (bookingEvent) params.set("event", bookingEvent.id);
    void navigate(`/admin/mail-campaigns?${params.toString()}`);
  };

  const { data, isLoading, isError, isPlaceholderData } = useSearchCompanies(
    {
      query: debouncedSearch.trim() || undefined,
      page,
      page_size: PAGE_SIZE,
      sort: sort?.field,
      direction: sort?.direction,
      filter,
      company: companyId ?? undefined,
    },
    { query: { placeholderData: keepPreviousData } },
  );

  const refreshCompanies = () =>
    queryClient.invalidateQueries({ queryKey: getSearchCompaniesQueryKey() });

  const { run: rename, isRunning: isRenaming } = useAsyncAction(
    async (companyId: string, name: string) => {
      await updateCompany(companyId, { name });
      await refreshCompanies();
      setRenamedId(null);
      notifySuccess(t("company_management.renamed"));
    },
  );

  const { run: confirm, isRunning: isConfirming } = useAsyncAction(
    async (company: CompanyListResult) => {
      await confirmCompany(
        company.id,
        { name: company.name },
        { quietStatuses: [CONFLICT] },
      );
      await refreshCompanies();
      notifySuccess(t("company_management.confirmed_notice"));
    },
    (error) => {
      if (getApiErrorStatus(error) !== CONFLICT) return;
      void refreshCompanies();
      notifyError(t("company_management.confirm_conflict"));
    },
  );

  const items = data?.items ?? [];
  const companyFilterLabel = companyId
    ? (items.find((company) => company.id === companyId)?.name ?? companyId)
    : null;
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (data && !isPlaceholderData && page > totalPages) setPage(totalPages);
  }, [data, isPlaceholderData, page, totalPages, setPage]);

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

        <CompanyFilters
          search={search}
          onSearchChange={setSearch}
          filter={filter}
          onFilterChange={setFilter}
          companyFilterLabel={companyFilterLabel}
          onClearCompany={clearCompany}
          events={events}
          eventId={bookingEvent?.id ?? null}
          onEventChange={pickEvent}
          isLoadingEvents={isLoadingEvents}
        />

        {isError ? (
          <ErrorAlert>{t("company_management.error")}</ErrorAlert>
        ) : isLoading ? (
          <PageLoader />
        ) : (
          <Paper withBorder p="lg" radius="md">
            {items.length === 0 ? (
              <Text c="dimmed">
                {t("company_management.no_companies_description")}
              </Text>
            ) : (
              <Table.ScrollContainer minWidth={700}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <SortableHeader
                        field="name"
                        label={t("company_management.company_name")}
                        sort={sort}
                        onSort={toggleSort}
                      />
                      <SortableHeader
                        field="members"
                        label={t("company_management.users_count")}
                        sort={sort}
                        onSort={toggleSort}
                      />
                      <SortableHeader
                        field="bookings"
                        label={t("company_management.bookings_count")}
                        sort={sort}
                        onSort={toggleSort}
                      />
                      {bookingEvent ? (
                        <Table.Th>{bookingEvent.name}</Table.Th>
                      ) : null}
                      <Table.Th>{t("company_management.actions")}</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {items.map((company) => {
                      const booking = activeBookingByCompanyId.get(company.id);
                      return (
                        <Table.Tr key={company.id}>
                          <Table.Td>
                            <CompanyNameCell
                              company={company}
                              isEditing={renamedId === company.id}
                              isSaving={isRenaming}
                              onCancel={() => setRenamedId(null)}
                              onEdit={() => setRenamedId(company.id)}
                              onSave={(name) => void rename(company.id, name)}
                            />
                          </Table.Td>
                          <Table.Td>{company.users_count}</Table.Td>
                          <Table.Td>{company.bookings_count}</Table.Td>
                          {bookingEvent ? (
                            <Table.Td>
                              {booking ? (
                                <CompanyBookingActions
                                  booking={booking}
                                  eventId={bookingEvent.id}
                                />
                              ) : null}
                            </Table.Td>
                          ) : null}
                          <Table.Td>
                            <CompanyRowActions
                              company={company}
                              canDelete={isAdmin}
                              canMail={canMail}
                              isConfirming={isConfirming}
                              onConfirm={() => void confirm(company)}
                              onDelete={() => setDeletedCompany(company)}
                              onMail={() => mailCompany(company.id)}
                              onShowMembers={() => setMembersCompany(company)}
                            />
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}

            <Group justify="space-between" mt="sm">
              <Text c="dimmed" size="sm">
                {t("company_management.total", { count: total })}
              </Text>
              <Pagination
                onChange={setPage}
                total={totalPages}
                value={page}
                withEdges
              />
            </Group>
          </Paper>
        )}
      </Stack>
    </Center>
  );
};

export default CompanyManagement;
