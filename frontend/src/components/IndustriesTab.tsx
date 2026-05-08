import {
  ActionIcon,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Table,
  Text,
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
  useCreateIndustry,
  useDeleteIndustry,
  useListIndustries,
} from "../orval/generated/kp/kp";
import ManageEntityModal from "./ManageEntityModal";

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

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.industries_title")}</Title>
        <Button leftSection={<IconPlus size={16} />} size="xs" onClick={open}>
          {t("kp.manage.industries_add")}
        </Button>
      </Group>

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

      {industries && industries.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.industry_name")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {industries.map((industry) => (
              <Table.Tr key={industry.id}>
                <Table.Td fw={500}>{industry.name}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.industry_confirm_delete"))) {
                        remove({ industryId: industry.id });
                      }
                    }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.industries_empty")}</Text>
      )}
    </Stack>
  );
};
export default IndustriesTab;
