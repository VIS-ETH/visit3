import {
  ActionIcon,
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconPlus,
  IconTrash,
  IconX,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../api/errors";
import type { IndustryResponse } from "../orval/generated/fastAPI.schemas";
import {
  getListIndustryCatalogueQueryKey,
  useCreateIndustryCatalogueEntry,
  useDeleteIndustryCatalogueEntry,
  useListIndustryCatalogue,
  useUpdateIndustryCatalogueEntry,
} from "../orval/generated/industry/industry";
import ManageEntityModal from "./ManageEntityModal";

const IndustriesTab = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: industries, isLoading } = useListIndustryCatalogue();
  const [isAddOpen, { open: openAdd, close: closeAdd }] = useDisclosure(false);
  const [newName, setNewName] = useState("");
  const [renamedId, setRenamedId] = useState<string | null>(null);
  const [renamedName, setRenamedName] = useState("");
  const [deleted, setDeleted] = useState<IndustryResponse | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListIndustryCatalogueQueryKey(),
    });

  const onError = (error: unknown) => {
    setErrorCode(getApiErrorCode(error) ?? "server.error");
  };

  const { mutate: create, isPending: isCreating } =
    useCreateIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          setNewName("");
          closeAdd();
          notifications.show({
            color: "green",
            message: t("industries.created"),
          });
        },
        onError,
      },
    });

  const { mutate: rename, isPending: isRenaming } =
    useUpdateIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          setRenamedId(null);
          notifications.show({
            color: "green",
            message: t("industries.renamed"),
          });
        },
        onError,
      },
    });

  const { mutate: remove, isPending: isDeleting } =
    useDeleteIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          setDeleted(null);
          notifications.show({
            color: "green",
            message: t("industries.deleted"),
          });
        },
        onError,
      },
    });

  return (
    <>
      <ManageEntityModal
        opened={isAddOpen}
        onClose={() => {
          setNewName("");
          closeAdd();
        }}
        title={t("industries.add")}
        isSaving={isCreating}
        isSubmitDisabled={!newName.trim()}
        submitLabel={t("industries.add")}
        onSubmit={() => {
          setErrorCode(null);
          create({ data: { name: newName.trim() } });
        }}
      >
        <TextInput
          label={t("industries.name")}
          value={newName}
          onChange={(event) => setNewName(event.currentTarget.value)}
          disabled={isCreating}
        />
      </ManageEntityModal>

      <Modal
        centered
        onClose={() => setDeleted(null)}
        opened={deleted !== null}
        title={t("industries.delete_modal.title")}
      >
        <Stack gap="sm">
          <Text>
            {t("industries.delete_modal.message", {
              name: deleted?.name ?? "",
            })}
          </Text>
          <Text c="dimmed" size="sm">
            {t("industries.delete_modal.usage_hint")}
          </Text>
          <Group justify="flex-end">
            <Button
              disabled={isDeleting}
              onClick={() => setDeleted(null)}
              variant="default"
            >
              {t("common.cancel")}
            </Button>
            <Button
              color="red"
              loading={isDeleting}
              onClick={() => {
                if (!deleted) return;
                setErrorCode(null);
                remove({ industryId: deleted.id });
              }}
            >
              {t("industries.delete_modal.confirm")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={4}>{t("industries.title")}</Title>
            <Button
              leftSection={<IconPlus size={16} />}
              size="xs"
              onClick={openAdd}
            >
              {t("industries.add")}
            </Button>
          </Group>

          {errorCode ? (
            <Alert
              color="red"
              icon={<IconAlertCircle />}
              title={t("error.title")}
            >
              {t(errorCode)}
            </Alert>
          ) : null}

          {isLoading ? (
            <Center py="md">
              <Loader />
            </Center>
          ) : !industries || industries.length === 0 ? (
            <Text c="dimmed">{t("industries.empty")}</Text>
          ) : (
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("industries.name")}</Table.Th>
                  <Table.Th w={120}>{t("industries.actions")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {industries.map((industry) => (
                  <Table.Tr key={industry.id}>
                    <Table.Td>
                      {renamedId === industry.id ? (
                        <TextInput
                          aria-label={t("industries.rename")}
                          disabled={isRenaming}
                          onChange={(event) =>
                            setRenamedName(event.currentTarget.value)
                          }
                          value={renamedName}
                        />
                      ) : (
                        industry.name
                      )}
                    </Table.Td>
                    <Table.Td>
                      {renamedId === industry.id ? (
                        <Group gap="xs" wrap="nowrap">
                          <ActionIcon
                            aria-label={t("industries.rename_save")}
                            color="green"
                            disabled={isRenaming || renamedName.trim() === ""}
                            onClick={() => {
                              setErrorCode(null);
                              rename({
                                industryId: industry.id,
                                data: { name: renamedName.trim() },
                              });
                            }}
                            variant="light"
                          >
                            <IconCheck size={16} />
                          </ActionIcon>
                          <ActionIcon
                            aria-label={t("industries.rename_cancel")}
                            disabled={isRenaming}
                            onClick={() => setRenamedId(null)}
                            variant="subtle"
                          >
                            <IconX size={16} />
                          </ActionIcon>
                        </Group>
                      ) : (
                        <Group gap="xs" wrap="nowrap">
                          <Button
                            onClick={() => {
                              setRenamedId(industry.id);
                              setRenamedName(industry.name);
                            }}
                            size="xs"
                            variant="light"
                          >
                            {t("industries.rename")}
                          </Button>
                          <ActionIcon
                            aria-label={t("industries.delete")}
                            color="red"
                            onClick={() => setDeleted(industry)}
                            variant="light"
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Group>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Stack>
      </Paper>
    </>
  );
};

export default IndustriesTab;
