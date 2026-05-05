import { Table, Paper } from "@mantine/core";
import React from "react";
import type {
  CompanyAssignedUserResponse,
  CompanyUserResponse,
  UserResponse,
} from "../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../utils/display";

type UserTableUser =
  | CompanyAssignedUserResponse
  | CompanyUserResponse
  | UserResponse;

interface UserTableProps {
  users: UserTableUser[];
  t: (key: string) => string;
  actionButton?: (user: UserTableUser) => React.ReactNode;
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
              {getDisplayName(user.first_name, user.last_name)}
            </Table.Td>
            <Table.Td>{user.phone_number || "-"}</Table.Td>
            {showCompany ? (
              <Table.Td>
                {"company" in user ? user.company?.name || "-" : "-"}
              </Table.Td>
            ) : null}
            {actionButton ? <Table.Td>{actionButton(user)}</Table.Td> : null}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  </Paper>
);

export default UserTable;
