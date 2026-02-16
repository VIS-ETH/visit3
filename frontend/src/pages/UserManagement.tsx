import { Center, Stack, Title, Table, Loader, Alert, Paper, Badge, Button } from "@mantine/core";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useConfirmUser, useGetUnconfirmedUsers } from "../orval/generated/user/user";
import { isStaff } from "../api/utils";
import NotAllowed from "../components/NotAllowed";

export default function UserManagement() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: users, isLoading, isError } = useGetUnconfirmedUsers();
  const staffStatus = isStaff();

  const { mutate: confirm, isPending: isConfirming, isError: isConfirmError } = useConfirmUser({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["/user/unconfirmed"] });
      },
    },
  });

  const handleConfirmUser = (userId: string | undefined) => {
    if (!userId) return;
    confirm({ userId });
  };

  if (!staffStatus) {
    return <NotAllowed />;
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={1000} gap="lg">
        <Title order={2}>{t("user_management.title")}</Title>

        {isLoading && (
          <Center py="xl">
            <Loader />
          </Center>
        )}

        {isError && (
          <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
            {t("user_management.error")}
          </Alert>
        )}

        {isConfirmError && (
          <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
            {t("user_management.confirm_error")}
          </Alert>
        )}

        {users && users.length === 0 && (
          <Alert icon={<IconAlertCircle />} color="blue" title={t("user_management.no_users")}>
            {t("user_management.no_users_description")}
          </Alert>
        )}

        {users && users.length > 0 && (
          <Paper withBorder p="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("user_management.email")}</Table.Th>
                  <Table.Th>{t("user_management.name")}</Table.Th>
                  <Table.Th>{t("user_management.status")}</Table.Th>
                  <Table.Th>{t("user_management.company")}</Table.Th>
                  <Table.Th style={{ width: 100 }}>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {users.map((user) => (
                  <Table.Tr key={user.id}>
                    <Table.Td>{user.email}</Table.Td>
                    <Table.Td>{user.first_name || "-"}</Table.Td>
                    <Table.Td>
                      <Badge color="yellow">{t("user_management.unconfirmed")}</Badge>
                    </Table.Td>
                    <Table.Td>{"-"}</Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconCheck size={14} />}
                        onClick={() => handleConfirmUser(user.id)}
                        disabled={isConfirming || !user.id}
                        loading={isConfirming}
                      >
                        {t("user_management.confirm")}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        )}
      </Stack>
    </Center>
  );
}
