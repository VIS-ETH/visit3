import {
  Alert,
  Badge,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useListStaffBookingNametags } from "../../orval/generated/kp/kp";

const BookingNametagsCard = ({ bookingId }: { bookingId: string }) => {
  const { t } = useTranslation();
  const {
    data: nameTags,
    isLoading,
    isError,
  } = useListStaffBookingNametags(bookingId, { query: { retry: false } });

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Title order={4}>{t("kp.nametags.staff_title")}</Title>
          <Badge variant="light">
            {t("kp.nametags.staff_count", { total: nameTags?.length ?? 0 })}
          </Badge>
        </Group>

        {isError ? (
          <Alert icon={<IconAlertCircle />} color="red">
            {t("kp.nametags.staff_load_error")}
          </Alert>
        ) : isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : nameTags && nameTags.length > 0 ? (
          <Table verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("kp.nametags.first_name")}</Table.Th>
                <Table.Th>{t("kp.nametags.last_name")}</Table.Th>
                <Table.Th>{t("kp.nametags.position")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {nameTags.map((nameTag) => (
                <Table.Tr key={nameTag.id}>
                  <Table.Td>{nameTag.first_name}</Table.Td>
                  <Table.Td>{nameTag.last_name}</Table.Td>
                  <Table.Td>{nameTag.position}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text c="dimmed">{t("kp.nametags.staff_empty")}</Text>
        )}
      </Stack>
    </Paper>
  );
};

export default BookingNametagsCard;
