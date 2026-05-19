import { Alert, Center, Paper, Stack, Title } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import {
  type GetCompanyWithUsersQueryResult,
  useGetCompanyWithUsers,
} from "../orval/generated/company/company";
import { getDisplayName } from "../utils/display";

type CompanyUserRow = GetCompanyWithUsersQueryResult["users"][number];

const CompanyUsers = () => {
  const { t } = useTranslation();
  const { companyId } = useParams<{ companyId: string }>();
  const {
    data: company,
    isLoading,
    isError,
  } = useGetCompanyWithUsers(companyId ?? "", {
    query: { enabled: Boolean(companyId) },
  });
  const users = company?.users;

  const columns: DataTableColumn<CompanyUserRow>[] = [
    {
      key: "name",
      header: t("company_management.user_name"),
      render: (user) => getDisplayName(user.first_name, user.last_name),
      searchableValue: (user) =>
        getDisplayName(user.first_name, user.last_name),
    },
    {
      key: "email",
      header: t("company_management.user_email"),
      render: (user) => user.email,
      searchableValue: (user) => user.email,
    },
    {
      key: "phone",
      header: t("company_management.user_phone"),
      render: (user) => user.phone_number ?? "-",
      searchableValue: (user) => user.phone_number ?? "",
    },
  ];

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1100} gap="lg">
        <BackButton to="/company-management" />
        <Title order={2}>
          {t("company_management.selected_users_title", {
            name: company?.name ?? t("company_management.company_fallback"),
          })}
        </Title>

        {isError ? (
          <Alert
            icon={<IconAlertCircle />}
            color="red"
            title={t("server.error")}
          >
            {t("company_management.users_error")}
          </Alert>
        ) : (
          <Paper withBorder p="lg" radius="md">
            <DataTable
              columns={columns}
              data={users}
              emptyLabel={t("company_management.no_users")}
              getRowKey={(user) => user.id}
              isLoading={isLoading}
            />
          </Paper>
        )}
      </Stack>
    </Center>
  );
};

export default CompanyUsers;
