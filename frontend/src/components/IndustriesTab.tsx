import {
  ActionIcon,
  Button,
  Group,
  Paper,
  Stack,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getListIndustriesQueryKey,
  type ListIndustriesQueryResult,
  useCreateIndustry,
  useDeleteIndustry,
  useListIndustries,
} from "../orval/generated/kp/kp";
import ManageEntityModal from "./ManageEntityModal";
import DataTable, { type DataTableColumn } from "./DataTable";

type IndustryRow = ListIndustriesQueryResult[number];

const IndustriesTab = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: industries, isLoading } = useListIndustries();
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListIndustriesQueryKey(),
    });

  const handleCloseModal = () => {
    close();
    setName("");
  };

  const { mutate: create, isPending: isCreating } = useCreateIndustry({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        handleCloseModal();
        notifications.show({
          color: "green",
          message: t("kp.manage.industry_created"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteIndustry({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.industry_deleted"),
        });
      },
    },
  });

  const columns: DataTableColumn<IndustryRow>[] = [
    {
      key: "name",
      header: t("kp.manage.industry_name"),
      render: (industry) => industry.name,
      searchableValue: (industry) => industry.name,
    },
    {
      key: "actions",
      header: "",
      render: (industry) => (
        <ActionIcon
          color="red"
          variant="subtle"
          aria-label={t("kp.manage.industry_confirm_delete")}
          onClick={() => {
            if (confirm(t("kp.manage.industry_confirm_delete"))) {
              remove({ industryId: industry.id });
            }
          }}
        >
          <IconTrash size={16} />
        </ActionIcon>
      ),
      width: 60,
    },
  ];

  return (
    <>
      <ManageEntityModal
        opened={opened}
        onClose={handleCloseModal}
        title={t("kp.manage.industries_add")}
        isSaving={isCreating}
        isSubmitDisabled={!name.trim()}
        submitLabel={t("kp.manage.industries_add")}
        onSubmit={() => create({ data: { name: name.trim() } })}
      >
        <TextInput
          label={t("kp.manage.industry_name")}
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          disabled={isCreating}
        />
      </ManageEntityModal>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={4}>{t("kp.manage.industries_title")}</Title>
            <Button
              leftSection={<IconPlus size={16} />}
              size="xs"
              onClick={open}
            >
              {t("kp.manage.industries_add")}
            </Button>
          </Group>

          <DataTable
            columns={columns}
            data={industries}
            emptyLabel={t("kp.manage.industries_empty")}
            getRowKey={(industry) => industry.id}
            isLoading={isLoading}
          />
        </Stack>
      </Paper>
    </>
  );
};
export default IndustriesTab;
