import {
  ActionIcon,
  Avatar,
  Button,
  Group,
  Paper,
  Stack,
  Switch,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import {
  getListServicesQueryKey,
  type ListServicesQueryResult,
  useDeleteService,
  useListServices,
  useUpdateService,
} from "../orval/generated/kp/kp";
import DataTable, { type DataTableColumn } from "./DataTable";

type ServiceRow = ListServicesQueryResult[number];

const ServicesTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: services, isLoading } = useListServices(eventId);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListServicesQueryKey(eventId),
    });

  const { mutate: update } = useUpdateService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_updated"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_deleted"),
        });
      },
    },
  });

  const columns: DataTableColumn<ServiceRow>[] = [
    {
      key: "name",
      header: t("kp.manage.service_name"),
      render: (service) => (
        <Group gap="sm" wrap="nowrap">
          <Avatar
            src={service.image_url}
            name={service.name}
            radius="sm"
            size={32}
          />
          {service.name}
        </Group>
      ),
      searchableValue: (service) => service.name,
    },
    {
      key: "price",
      header: t("kp.manage.service_price"),
      render: (service) => (service.price / 100).toFixed(2),
      searchableValue: (service) => (service.price / 100).toFixed(2),
    },
    {
      key: "max-per-booking",
      header: t("kp.manage.service_max_per_booking"),
      render: (service) => service.max_quantity_per_booking,
      searchableValue: (service) => String(service.max_quantity_per_booking),
    },
    {
      key: "requirements",
      header: t("kp.manage.service_requirements"),
      render: (service) => service.requirements.length,
      searchableValue: (service) => String(service.requirements.length),
      textAlign: "right",
      width: 130,
    },
    {
      key: "active",
      header: t("kp.manage.service_active"),
      render: (service) => (
        <Switch
          checked={service.is_active}
          onChange={(e) =>
            update({
              serviceId: service.id,
              data: { is_active: e.currentTarget.checked },
            })
          }
          size="sm"
        />
      ),
      searchableValue: (service) =>
        service.is_active
          ? t("kp.manage.service_active_yes")
          : t("kp.manage.service_active_no"),
    },
    {
      key: "actions",
      header: "",
      render: (service) => (
        <Group gap="xs">
          <ActionIcon
            component={Link}
            to={`/kp/${eventId}/services/${service.id}`}
            variant="subtle"
            aria-label={t("kp.manage.services_edit")}
          >
            <IconEdit size={16} />
          </ActionIcon>
          <ActionIcon
            color="red"
            variant="subtle"
            aria-label={t("kp.manage.service_confirm_delete")}
            onClick={() => {
              if (confirm(t("kp.manage.service_confirm_delete"))) {
                remove({ serviceId: service.id });
              }
            }}
          >
            <IconTrash size={16} />
          </ActionIcon>
        </Group>
      ),
      width: 90,
    },
  ];

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={4}>{t("kp.manage.services_title")}</Title>
          <Button
            component={Link}
            to={`/kp/${eventId}/services/new`}
            leftSection={<IconPlus size={16} />}
            size="xs"
          >
            {t("kp.manage.services_add")}
          </Button>
        </Group>

        <DataTable
          columns={columns}
          data={services}
          emptyLabel={t("kp.manage.services_empty")}
          getRowKey={(service) => service.id}
          isLoading={isLoading}
        />
      </Stack>
    </Paper>
  );
};
export default ServicesTab;
