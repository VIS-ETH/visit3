import { Button, Group, Paper, Stack, Switch, Title } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { StaffBoothZoneResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getListBoothZonesQueryKey,
  useDeleteBoothZone,
  useListBoothZones,
  useListServices,
  useReorderBoothZones,
  useUpdateBoothZone,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { notifySuccess } from "../../utils/notify";
import { swapped } from "../../utils/swapped";
import DataTable, { type DataTableColumn } from "../DataTable";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import BoothZoneFormModal from "./booth-zones/BoothZoneFormModal";
import BoothZoneRowActions from "./booth-zones/BoothZoneRowActions";

const BoothZonesTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const queryKey = getListBoothZonesQueryKey(eventId);
  const { data: zones, isLoading, isError } = useListBoothZones(eventId);
  const { data: services } = useListServices(eventId);
  const [modal, setModal] = useState<{
    zone: StaffBoothZoneResponse | null;
  } | null>(null);

  const { mutateAsync: remove } = useDeleteBoothZone();
  const { mutateAsync: reorder } = useReorderBoothZones();
  const { mutateAsync: update } = useUpdateBoothZone();

  const { run: runZoneAction, isRunning: isBusy } = useAsyncAction(
    async (action: () => Promise<unknown>) => {
      await action();
      await queryClient.invalidateQueries({ queryKey });
    },
  );

  const deleteZone = (zone: StaffBoothZoneResponse) =>
    runZoneAction(async () => {
      await remove({ boothZoneId: zone.id });
      notifySuccess(t("kp.manage.zone_deleted"));
    });

  const zoneIds = (zones ?? []).map((zone) => zone.id);
  const moveZone = (zone: StaffBoothZoneResponse, offset: number) => {
    const index = zoneIds.indexOf(zone.id);
    void runZoneAction(async () => {
      const reordered = await reorder({
        eventId,
        data: { booth_zone_ids: swapped(zoneIds, index, index + offset) },
      });
      queryClient.setQueryData(queryKey, reordered);
    });
  };

  const toggleRegistration = (zone: StaffBoothZoneResponse, open: boolean) =>
    runZoneAction(() =>
      update({ boothZoneId: zone.id, data: { registration_open: open } }),
    );

  const columns: DataTableColumn<StaffBoothZoneResponse>[] = [
    {
      key: "color",
      header: "",
      render: (zone) => <KpBoothZoneColorSwatch color={zone.color} size={16} />,
      searchableValue: (zone) => zone.color,
      width: 40,
    },
    {
      key: "name",
      header: t("kp.manage.zone_name"),
      render: (zone) => zone.name,
      searchableValue: (zone) => zone.name,
    },
    {
      key: "capacity",
      header: t("kp.manage.zone_capacity"),
      render: (zone) => zone.capacity,
      searchableValue: (zone) => String(zone.capacity),
    },
    {
      key: "booth-size",
      header: t("kp.manage.zone_booth_size"),
      render: (zone) => `${zone.booth_size} m²`,
      searchableValue: (zone) => String(zone.booth_size),
    },
    {
      key: "base-price",
      header: t("kp.manage.zone_base_price"),
      render: (zone) => (zone.base_price / 100).toFixed(2),
      searchableValue: (zone) => (zone.base_price / 100).toFixed(2),
    },
    {
      key: "included-services",
      header: t("kp.manage.zone_included_services"),
      render: (zone) => zone.included_services.length,
      searchableValue: (zone) => String(zone.included_services.length),
      textAlign: "right",
      width: 150,
    },
    {
      key: "registration",
      header: t("kp.manage.zone_registration"),
      render: (zone) => (
        <Switch
          aria-label={t("kp.manage.zone_registration_open")}
          checked={zone.registration_open}
          disabled={isBusy}
          onChange={(event) => {
            void toggleRegistration(zone, event.currentTarget.checked);
          }}
        />
      ),
      searchableValue: (zone) => String(zone.registration_open),
      width: 120,
    },
    {
      key: "actions",
      header: "",
      render: (zone) => (
        <BoothZoneRowActions
          canMoveUp={zone.id !== zoneIds.at(0)}
          canMoveDown={zone.id !== zoneIds.at(-1)}
          isBusy={isBusy}
          onMove={(offset) => moveZone(zone, offset)}
          onEdit={() => setModal({ zone })}
          onDelete={() => {
            void deleteZone(zone);
          }}
        />
      ),
      width: 160,
    },
  ];

  return (
    <>
      {modal ? (
        <BoothZoneFormModal
          eventId={eventId}
          zone={modal.zone}
          services={services ?? []}
          opened
          onClose={() => setModal(null)}
        />
      ) : null}

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={4}>{t("kp.manage.booth_zones_title")}</Title>
            <Button
              leftSection={<IconPlus size={16} />}
              size="xs"
              onClick={() => setModal({ zone: null })}
            >
              {t("kp.manage.booth_zones_add")}
            </Button>
          </Group>

          <DataTable
            columns={columns}
            data={zones}
            emptyLabel={t("kp.manage.booth_zones_empty")}
            getRowKey={(zone) => zone.id}
            isLoading={isLoading}
            isError={isError}
          />
        </Stack>
      </Paper>
    </>
  );
};
export default BoothZonesTab;
