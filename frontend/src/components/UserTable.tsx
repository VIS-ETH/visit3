import { Table, Paper } from "@mantine/core";
import React from "react";

interface Company {
  name?: string | null;
}

interface User {
  id?: string;
  email?: string;
  first_name?: string | null;
  last_name?: string | null;
  phone_number?: string | null;
  company?: Company | null;
}

interface UserTableProps {
  users: User[];
  t: (key: string) => string;
  actionButton?: (user: User) => React.ReactNode;
  showCompany?: boolean;
}

const UserTable: React.FC<UserTableProps> = ({
  users,
  t,
  actionButton,
  showCompany = true,
}) => (
  <Paper withBorder p="md">
    <Table striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>{t("user_management.email")}</Table.Th>
          <Table.Th>{t("user_management.name")}</Table.Th>
          <Table.Th>{t("user_management.phone")}</Table.Th>
          {showCompany ? (
            <Table.Th>{t("user_management.company")}</Table.Th>
          ) : null}
          {actionButton ? (
            <Table.Th style={{ width: 100 }}>
              {t("user_management.actions")}
            </Table.Th>
          ) : null}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {users.map((user) => (
          <Table.Tr key={user.id}>
            <Table.Td>{user.email}</Table.Td>
            <Table.Td>
              {!user.first_name && !user.last_name
                ? "-"
                : `${user.first_name ? user.first_name + " " : ""}${user.last_name ? user.last_name : ""}`}
            </Table.Td>
            <Table.Td>{user.phone_number || "-"}</Table.Td>
            {showCompany ? (
              <Table.Td>{user.company?.name || "-"}</Table.Td>
            ) : null}
            {actionButton ? <Table.Td>{actionButton(user)}</Table.Td> : null}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  </Paper>
);

export default UserTable;
