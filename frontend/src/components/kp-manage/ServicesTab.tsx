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
import { notifySuccess } from "../../utils/notify";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import {
  getListServicesQueryKey,
  type ListServicesQueryResult,
  useDeleteService,
  useListServices,
  useUpdateService,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { servicesOfCategory } from "../../utils/kp-service-quantity";
import DataTable, { type DataTableColumn } from "../DataTable";
import ErrorAlert from "../ErrorAlert";

type ServiceRow = ListServicesQueryResult[number];

const ServicesTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: services, isLoading, isError } = useListServices(eventId);
  const { mutateAsync: update } = useUpdateService();
  const { mutateAsync: remove } = useDeleteService();

  const { run: runServiceAction, isRunning: isBusy } = useAsyncAction(
    async (action: () => Promise<unknown>, successMessage: string) => {
      await action();
      await queryClient.invalidateQueries({
        queryKey: getListServicesQueryKey(eventId),
      });
      notifySuccess(successMessage);
    },
  );

  const columns: DataTableColumn<ServiceRow>[] = [
    {
      key: "name",
      sortValue: (service) => service.name,
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
      sortValue: (service) => service.price,
      header: t("kp.manage.service_price"),
      render: (service) => (service.price / 100).toFixed(2),
      searchableValue: (service) => (service.price / 100).toFixed(2),
    },
    {
      key: "max-per-booking",
      sortValue: (service) => service.max_quantity_per_booking,
      header: t("kp.manage.service_max_per_booking"),
      render: (service) => service.max_quantity_per_booking,
      searchableValue: (service) => String(service.max_quantity_per_booking),
    },
    {
      key: "requirements",
      sortValue: (service) => service.requirements.length,
      header: t("kp.manage.service_requirements"),
      render: (service) => service.requirements.length,
      searchableValue: (service) => String(service.requirements.length),
      textAlign: "right",
      width: 130,
    },
    {
      key: "active",
      sortValue: (service) => Number(service.is_active),
      header: t("kp.manage.service_active"),
      render: (service) => (
        <Switch
          aria-label={t("kp.manage.service_active_toggle", {
            name: service.name,
          })}
          checked={service.is_active}
          disabled={isBusy}
          onChange={(event) => {
            const isActive = event.currentTarget.checked;
            void runServiceAction(
              () =>
                update({
                  serviceId: service.id,
                  data: { is_active: isActive },
                }),
              t("kp.manage.service_updated"),
            );
          }}
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
            disabled={isBusy}
            onClick={() => {
              if (confirm(t("kp.manage.service_confirm_delete"))) {
                void runServiceAction(
                  () => remove({ serviceId: service.id }),
                  t("kp.manage.service_deleted"),
                );
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

  const groups = [
    {
      title: t("kp.manage.services_group_services"),
      emptyLabel: t("kp.manage.services_group_services_empty"),
      category: KpServiceCategory.SERVICE,
    },
    {
      title: t("kp.manage.services_group_booth_elements"),
      emptyLabel: t("kp.manage.services_group_booth_elements_empty"),
      category: KpServiceCategory.BOOTH_ELEMENT,
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

        {isError ? (
          <ErrorAlert />
        ) : (
          groups.map((group) => (
            <Stack gap="xs" key={group.category}>
              <Title order={5}>{group.title}</Title>
              <DataTable
                columns={columns}
                data={
                  services
                    ? servicesOfCategory(services, group.category)
                    : undefined
                }
                emptyLabel={group.emptyLabel}
                getRowKey={(service) => service.id}
                isLoading={isLoading}
              />
            </Stack>
          ))
        )}
      </Stack>
    </Paper>
  );
};
export default ServicesTab;
