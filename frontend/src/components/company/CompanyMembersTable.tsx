import { Paper, Table, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useGetMyCompanyMembers } from "../../orval/generated/company/company";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";

const CompanyMembersTable = () => {
  const { t } = useTranslation();
  const { data: members = [], isLoading, isError } = useGetMyCompanyMembers();

  if (isLoading) return <PageLoader />;
  if (isError) return <ErrorAlert />;
  if (members.length === 0) {
    return <Text c="dimmed">{t("company_profile.no_members")}</Text>;
  }

  return (
    <Paper withBorder radius="md" style={{ overflow: "hidden" }}>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t("user_management.name")}</Table.Th>
            <Table.Th>{t("user_management.email")}</Table.Th>
            <Table.Th>{t("user_management.phone")}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {members.map((m) => (
            <Table.Tr key={m.id}>
              <Table.Td>
                {[m.first_name, m.last_name].filter(Boolean).join(" ") || "-"}
              </Table.Td>
              <Table.Td>{m.email}</Table.Td>
              <Table.Td>{m.phone_number ?? "-"}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  );
};

export default CompanyMembersTable;
