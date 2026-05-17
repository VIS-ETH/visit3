import { Paper } from "@mantine/core";
import type { ReactNode } from "react";
import type {
  CompanyUserResponse,
  UserResponse,
} from "../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../utils/display";
import DataTable, { type DataTableColumn } from "./DataTable";

type UserTableUser = CompanyUserResponse | UserResponse;

interface UserTableProps {
  users: UserTableUser[];
  t: (key: string, options?: Record<string, unknown>) => string;
  actionButton?: (user: UserTableUser) => ReactNode;
  showCompany?: boolean;
}

const UserTable = ({
  users,
  t,
  actionButton,
  showCompany = true,
}: UserTableProps) => {
  const columns: DataTableColumn<UserTableUser>[] = [
    {
      key: "email",
      header: t("user_management.email"),
      render: (user) => user.email,
      searchableValue: (user) => user.email,
    },
    {
      key: "name",
      header: t("user_management.name"),
      render: (user) => getDisplayName(user.first_name, user.last_name),
      searchableValue: (user) =>
        getDisplayName(user.first_name, user.last_name),
    },
    {
      key: "phone",
      header: t("user_management.phone"),
      render: (user) => user.phone_number ?? "-",
      searchableValue: (user) => user.phone_number ?? "",
    },
  ];

  if (showCompany) {
    columns.push({
      key: "company",
      header: t("user_management.company"),
      render: (user) => ("company" in user ? (user.company?.name ?? "-") : "-"),
      searchableValue: (user) =>
        "company" in user ? (user.company?.name ?? "") : "",
    });
  }

  if (actionButton) {
    columns.push({
      key: "actions",
      header: t("user_management.actions"),
      render: actionButton,
      width: 100,
    });
  }

  return (
    <Paper withBorder p="lg" radius="md">
      <DataTable
        columns={columns}
        data={users}
        emptyLabel={t("user_management.table_empty")}
        getRowKey={(user) => user.id}
        pagination={{
          pageSummary: (first, last, total) =>
            t("user_management.table_page_summary", { first, last, total }),
          rowsPerPage: t("user_management.table_rows_per_page"),
        }}
        search={{
          noResults: t("user_management.table_no_results"),
          placeholder: t("user_management.table_search_placeholder"),
        }}
      />
    </Paper>
  );
};
export default UserTable;
