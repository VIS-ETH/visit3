import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconDeviceFloppy,
  IconId,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import {
  KpBookingStatus,
  type BookingResponse,
  type KpResponse,
  type NameTagInput,
} from "../../orval/generated/fastAPI.schemas";
import {
  getListBookingNametagsQueryKey,
  useListBookingNametags,
  useReplaceBookingNametags,
} from "../../orval/generated/kp/kp";
import { formatKpDisplayDate, isDeadlinePassed } from "../../utils/kp-utils";

const EDITABLE_STATUSES: readonly KpBookingStatus[] = [
  KpBookingStatus.REGISTERED,
  KpBookingStatus.CONFIRMED,
];

const emptyNameTag: NameTagInput = {
  first_name: "",
  last_name: "",
  position: "",
};

const trimNameTags = (nameTags: NameTagInput[]): NameTagInput[] =>
  nameTags.map((nameTag) => ({
    first_name: nameTag.first_name.trim(),
    last_name: nameTag.last_name.trim(),
    position: nameTag.position.trim(),
  }));

const isFilled = (nameTags: NameTagInput[]) =>
  trimNameTags(nameTags).every(
    (nameTag) => nameTag.first_name && nameTag.last_name && nameTag.position,
  );

const sameNameTags = (left: NameTagInput[], right: NameTagInput[]) =>
  JSON.stringify(trimNameTags(left)) === JSON.stringify(trimNameTags(right));

interface NametagCardProps {
  event: KpResponse;
  booking: BookingResponse;
}

const NametagCard = ({ event, booking }: NametagCardProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<NameTagInput[] | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const {
    data: nameTags,
    isLoading,
    isError,
  } = useListBookingNametags(booking.id);
  const { mutateAsync: replaceNameTags, isPending } =
    useReplaceBookingNametags();

  const savedNameTags = useMemo(() => trimNameTags(nameTags ?? []), [nameTags]);
  const rows = draft ?? savedNameTags;
  const hasUnsavedChanges =
    draft !== null && !sameNameTags(draft, savedNameTags);

  const deadlinePassed = isDeadlinePassed(event.nametags_deadline);
  const statusAllowsEditing = EDITABLE_STATUSES.includes(booking.status);
  const isEditable = statusAllowsEditing && !deadlinePassed;
  const limitReached = rows.length >= event.max_nametags_per_booking;

  const updateRow = (index: number, field: keyof NameTagInput, value: string) =>
    setDraft(
      rows.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row,
      ),
    );

  const addRow = () => setDraft([...rows, emptyNameTag]);

  const removeRow = (index: number) =>
    setDraft(rows.filter((_, rowIndex) => rowIndex !== index));

  const save = async () => {
    setErrorCode(null);
    try {
      await replaceNameTags({
        bookingId: booking.id,
        data: { name_tags: trimNameTags(rows) },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "server.error");
      return;
    }
    setDraft(null);
    await queryClient.invalidateQueries({
      queryKey: getListBookingNametagsQueryKey(booking.id),
    });
    notifications.show({ color: "green", message: t("kp.nametags.saved") });
  };

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start">
          <Group gap="sm">
            <IconId size={22} />
            <Title order={4}>{t("kp.nametags.title")}</Title>
          </Group>
          <Group gap="xs">
            {hasUnsavedChanges ? (
              <Badge color="yellow" variant="light">
                {t("kp.nametags.unsaved")}
              </Badge>
            ) : null}
            <Badge variant="light">
              {t("kp.nametags.counter", {
                used: rows.length,
                max: event.max_nametags_per_booking,
              })}
            </Badge>
          </Group>
        </Group>

        <Text c="dimmed" size="sm">
          {t("kp.nametags.description")}
        </Text>
        <Text c="dimmed" size="sm">
          {t("kp.nametags.deadline", {
            date: formatKpDisplayDate(event.nametags_deadline),
          })}
        </Text>

        {!statusAllowsEditing ? (
          <Alert icon={<IconAlertCircle />} color="yellow">
            {t("kp.nametags.booking_closed")}
          </Alert>
        ) : deadlinePassed ? (
          <Alert icon={<IconAlertCircle />} color="yellow">
            {t("kp.nametags.deadline_passed")}
          </Alert>
        ) : null}

        {errorCode ? (
          <Alert icon={<IconAlertCircle />} color="red">
            {t(errorCode)}
          </Alert>
        ) : null}

        {isError ? (
          <Alert icon={<IconAlertCircle />} color="red">
            {t("kp.nametags.load_error")}
          </Alert>
        ) : null}

        {isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : rows.length === 0 ? (
          <Text size="sm">{t("kp.nametags.empty")}</Text>
        ) : (
          <Table verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("kp.nametags.first_name")}</Table.Th>
                <Table.Th>{t("kp.nametags.last_name")}</Table.Th>
                <Table.Th>{t("kp.nametags.position")}</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row, index) => (
                <Table.Tr key={index}>
                  <Table.Td>
                    <TextInput
                      aria-label={t("kp.nametags.first_name")}
                      disabled={!isEditable}
                      onChange={(changeEvent) =>
                        updateRow(
                          index,
                          "first_name",
                          changeEvent.currentTarget.value,
                        )
                      }
                      size="sm"
                      value={row.first_name}
                    />
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      aria-label={t("kp.nametags.last_name")}
                      disabled={!isEditable}
                      onChange={(changeEvent) =>
                        updateRow(
                          index,
                          "last_name",
                          changeEvent.currentTarget.value,
                        )
                      }
                      size="sm"
                      value={row.last_name}
                    />
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      aria-label={t("kp.nametags.position")}
                      disabled={!isEditable}
                      onChange={(changeEvent) =>
                        updateRow(
                          index,
                          "position",
                          changeEvent.currentTarget.value,
                        )
                      }
                      size="sm"
                      value={row.position}
                    />
                  </Table.Td>
                  <Table.Td w={48}>
                    <ActionIcon
                      aria-label={t("kp.nametags.remove")}
                      color="red"
                      disabled={!isEditable || isPending}
                      onClick={() => removeRow(index)}
                      variant="subtle"
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}

        {isEditable && limitReached ? (
          <Text c="dimmed" size="sm">
            {t("kp.nametags.limit_reached")}
          </Text>
        ) : null}

        {isEditable && !isFilled(rows) ? (
          <Text c="dimmed" size="sm">
            {t("kp.nametags.incomplete")}
          </Text>
        ) : null}

        {isEditable ? (
          <Group justify="flex-end">
            <Button
              disabled={limitReached}
              leftSection={<IconPlus size={16} />}
              onClick={addRow}
              variant="light"
            >
              {t("kp.nametags.add")}
            </Button>
            <Button
              disabled={!hasUnsavedChanges || !isFilled(rows)}
              leftSection={<IconDeviceFloppy size={16} />}
              loading={isPending}
              onClick={() => {
                void save();
              }}
            >
              {t("kp.nametags.save")}
            </Button>
          </Group>
        ) : null}
      </Stack>
    </Card>
  );
};

export default NametagCard;
