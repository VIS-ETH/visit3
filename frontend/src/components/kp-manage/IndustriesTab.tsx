import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifySuccess } from "../../utils/notify";
import { IconCheck, IconPlus, IconTrash, IconX } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import type { IndustryResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getListIndustryCatalogueQueryKey,
  useCreateIndustryCatalogueEntry,
  useDeleteIndustryCatalogueEntry,
  useListIndustryCatalogue,
  useUpdateIndustryCatalogueEntry,
} from "../../orval/generated/industry/industry";
import ErrorAlert from "../ErrorAlert";
import ManageEntityModal from "../ManageEntityModal";
import PageLoader from "../PageLoader";

const HANDLED_STATUSES = [400, 404, 409];

const ActionError = ({ code }: { code: string | null }) => {
  const { t } = useTranslation();
  if (!code) return null;
  return <ErrorAlert>{t(code)}</ErrorAlert>;
};

const IndustriesTab = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const {
    data: industries,
    isLoading,
    isError: isLoadError,
  } = useListIndustryCatalogue();
  const [isAddOpen, { open: openAdd, close: closeAdd }] = useDisclosure(false);
  const [newName, setNewName] = useState("");
  const [renamedId, setRenamedId] = useState<string | null>(null);
  const [renamedName, setRenamedName] = useState("");
  const [deleted, setDeleted] = useState<IndustryResponse | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListIndustryCatalogueQueryKey(),
    });

  const errorHandler =
    (setError: (code: string | null) => void) => (error: unknown) => {
      setError(getApiErrorCode(error) ?? "server.error");
    };
  const request = { quietStatuses: HANDLED_STATUSES };

  const closeAddModal = () => {
    setNewName("");
    setCreateError(null);
    closeAdd();
  };

  const closeDeleteModal = () => {
    setDeleted(null);
    setDeleteError(null);
  };

  const { mutate: create, isPending: isCreating } =
    useCreateIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          closeAddModal();
          notifySuccess(t("industries.created"));
        },
        onError: errorHandler(setCreateError),
      },
      request,
    });

  const { mutate: rename, isPending: isRenaming } =
    useUpdateIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          setRenamedId(null);
          notifySuccess(t("industries.renamed"));
        },
        onError: errorHandler(setRenameError),
      },
      request,
    });

  const { mutate: remove, isPending: isDeleting } =
    useDeleteIndustryCatalogueEntry({
      mutation: {
        onSuccess: async () => {
          await invalidate();
          closeDeleteModal();
          notifySuccess(t("industries.deleted"));
        },
        onError: errorHandler(setDeleteError),
      },
      request,
    });

  return (
    <>
      <ManageEntityModal
        opened={isAddOpen}
        onClose={closeAddModal}
        title={t("industries.add")}
        isSaving={isCreating}
        isSubmitDisabled={!newName.trim()}
        submitLabel={t("industries.add")}
        onSubmit={() => {
          setCreateError(null);
          create({ data: { name: newName.trim() } });
        }}
      >
        <ActionError code={createError} />
        <TextInput
          label={t("industries.name")}
          value={newName}
          onChange={(event) => setNewName(event.currentTarget.value)}
          disabled={isCreating}
        />
      </ManageEntityModal>

      <Modal
        centered
        onClose={closeDeleteModal}
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
          <ActionError code={deleteError} />
          <Group justify="flex-end">
            <Button
              disabled={isDeleting}
              onClick={closeDeleteModal}
              variant="default"
            >
              {t("common.cancel")}
            </Button>
            <Button
              color="red"
              loading={isDeleting}
              onClick={() => {
                if (!deleted) return;
                setDeleteError(null);
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

          <ActionError code={renameError} />

          {isLoadError ? (
            <ErrorAlert />
          ) : isLoading ? (
            <PageLoader />
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
                              setRenameError(null);
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
