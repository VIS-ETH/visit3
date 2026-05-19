import {
  Alert,
  Button,
  Center,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconTrash, IconUsers } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  getListCompaniesQueryKey,
  type ListCompaniesQueryResult,
  useDeleteCompanyKeepUsers,
  useDeleteCompanyWithUsers,
  useListCompanies,
} from "../orval/generated/company/company";
import { useCurrentUser } from "../context/useCurrentUser";
import DataTable, { type DataTableColumn } from "../components/DataTable";

interface CompanyForDelete {
  id: string;
  name: string;
  usersCount: number;
}

type CompanyRow = ListCompaniesQueryResult[number];

const CompanyManagement = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const staffStatus = user?.is_staff ?? false;
  const adminStatus = user?.is_admin ?? false;
  const [deleteModalOpened, setDeleteModalOpened] = useState(false);
  const [companyToDelete, setCompanyToDelete] =
    useState<CompanyForDelete | null>(null);
  const {
    data: companies,
    isLoading,
    isError,
  } = useListCompanies({
    query: {
      enabled: staffStatus,
    },
  });

  const { mutate: deleteCompanyKeepUsers, isPending: isDeletingKeepUsers } =
    useDeleteCompanyKeepUsers({
      mutation: {
        onSuccess: () => {
          queryClient.invalidateQueries({
            queryKey: getListCompaniesQueryKey(),
          });
          setDeleteModalOpened(false);
        },
      },
    });

  const { mutate: deleteCompanyWithUsers, isPending: isDeletingWithUsers } =
    useDeleteCompanyWithUsers({
      mutation: {
        onSuccess: () => {
          queryClient.invalidateQueries({
            queryKey: getListCompaniesQueryKey(),
          });
          setDeleteModalOpened(false);
        },
      },
    });

  const isDeleting = isDeletingKeepUsers || isDeletingWithUsers;

  const handleOpenDeleteModal = (
    companyId: string,
    companyName: string,
    usersCount: number,
  ) => {
    if (!adminStatus) return;
    setCompanyToDelete({
      id: companyId,
      name: companyName,
      usersCount,
    });
    setDeleteModalOpened(true);
  };

  const handleDeleteKeepUsers = () => {
    if (!adminStatus) return;
    if (!companyToDelete?.id) return;
    deleteCompanyKeepUsers({ companyId: companyToDelete.id });
  };

  const handleDeleteWithUsers = () => {
    if (!adminStatus) return;
    if (!companyToDelete?.id) return;
    deleteCompanyWithUsers({ companyId: companyToDelete.id });
  };

  const companyHasUsers = (companyToDelete?.usersCount ?? 0) > 0;

  const companyColumns: DataTableColumn<CompanyRow>[] = [
    {
      key: "name",
      header: t("company_management.company_name"),
      render: (company) => company.name,
      searchableValue: (company) => company.name,
    },
    {
      key: "users",
      header: t("company_management.users_count"),
      render: (company) => company.users_count,
      searchableValue: (company) => String(company.users_count),
    },
    {
      key: "actions",
      header: t("company_management.actions"),
      render: (company) => (
        <Group gap="xs">
          <Button
            component={Link}
            to={`/company-management/${company.id}/users`}
            leftSection={<IconUsers size={14} />}
            size="xs"
            variant="light"
          >
            {t("company_management.view_users")}
          </Button>
          {adminStatus ? (
            <Button
              leftSection={<IconTrash size={14} />}
              size="xs"
              color="red"
              variant="light"
              onClick={() =>
                handleOpenDeleteModal(
                  company.id,
                  company.name,
                  company.users_count,
                )
              }
            >
              {t("company_management.delete")}
            </Button>
          ) : null}
        </Group>
      ),
      width: adminStatus ? 220 : 120,
    },
  ];

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1100} gap="lg">
        <Title order={2}>{t("company_management.title")}</Title>

        <Modal
          opened={adminStatus && deleteModalOpened}
          onClose={() => {
            if (!isDeleting) {
              setDeleteModalOpened(false);
            }
          }}
          onExitTransitionEnd={() => {
            if (!deleteModalOpened) {
              setCompanyToDelete(null);
            }
          }}
          closeOnClickOutside={!isDeleting}
          closeOnEscape={!isDeleting}
          withCloseButton={!isDeleting}
          title={t("company_management.delete_modal.title")}
          centered
        >
          <Stack gap="sm">
            <Text>
              {t("company_management.delete_modal.message", {
                name: companyToDelete?.name ?? "-",
              })}
            </Text>
            <Text c="red" fw={600}>
              {t("company_management.delete_modal.irreversible")}
            </Text>
            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => setDeleteModalOpened(false)}
                disabled={isDeleting}
              >
                {t("company_management.delete_modal.cancel")}
              </Button>
              {companyHasUsers ? (
                <>
                  <Button
                    color="yellow"
                    onClick={handleDeleteKeepUsers}
                    loading={isDeletingKeepUsers}
                    disabled={!companyToDelete?.id || isDeleting}
                  >
                    {t("company_management.delete_modal.keep_users")}
                  </Button>
                  <Button
                    color="red"
                    onClick={handleDeleteWithUsers}
                    loading={isDeletingWithUsers}
                    disabled={!companyToDelete?.id || isDeleting}
                  >
                    {t("company_management.delete_modal.delete_with_users")}
                  </Button>
                </>
              ) : (
                <Button
                  color="red"
                  onClick={handleDeleteKeepUsers}
                  loading={isDeletingKeepUsers}
                  disabled={!companyToDelete?.id || isDeleting}
                >
                  {t("company_management.delete")}
                </Button>
              )}
            </Group>
          </Stack>
        </Modal>

        {isError ? (
          <Alert
            icon={<IconAlertCircle />}
            color="red"
            title={t("server.error")}
          >
            {t("company_management.error")}
          </Alert>
        ) : (
          <Paper withBorder p="lg" radius="md">
            <DataTable
              columns={companyColumns}
              data={companies}
              emptyLabel={t("company_management.no_companies_description")}
              getRowKey={(company) => company.id}
              isLoading={isLoading}
            />
          </Paper>
        )}
      </Stack>
    </Center>
  );
};
export default CompanyManagement;
