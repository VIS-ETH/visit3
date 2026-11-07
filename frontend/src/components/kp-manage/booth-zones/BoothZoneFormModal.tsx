import {
  ColorInput,
  Divider,
  Group,
  NumberInput,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode, getApiErrorStatus } from "../../../api/errors";
import type {
  ServiceResponse,
  StaffBoothZoneResponse,
} from "../../../orval/generated/fastAPI.schemas";
import {
  getListBoothZonesQueryKey,
  useCreateBoothZone,
  useUpdateBoothZone,
} from "../../../orval/generated/kp/kp";
import { useAsyncAction } from "../../../hooks/use-async-action";
import { boothZoneSchema } from "../../../schemas/kpSchema";
import { notifySuccess } from "../../../utils/notify";
import { useTranslatedForm } from "../../../utils/translator";
import ErrorAlert from "../../ErrorAlert";
import ManageEntityModal from "../../ManageEntityModal";
import IncludedServicesEditor from "../IncludedServicesEditor";
import BoothZoneLayoutField from "./BoothZoneLayoutField";
import {
  emptyZoneValues,
  toZoneFormValues,
  toZoneRequest,
} from "./booth-zone-form";
import { useZoneLayoutFile } from "./use-zone-layout-file";

const REFUSED_SAVE_STATUSES = [400, 404, 409, 422];
const quietRefusals = { request: { quietStatuses: REFUSED_SAVE_STATUSES } };

const BoothZoneFormModal = ({
  eventId,
  zone,
  services,
  opened,
  onClose,
}: {
  eventId: string;
  zone: StaffBoothZoneResponse | null;
  services: ServiceResponse[];
  opened: boolean;
  onClose: () => void;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [createdZoneId, setCreatedZoneId] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const layout = useZoneLayoutFile(zone?.layout_url ?? null);
  const form = useTranslatedForm<typeof boothZoneSchema>(boothZoneSchema, {
    initialValues: zone ? toZoneFormValues(zone) : emptyZoneValues,
  });
  const { mutateAsync: create } = useCreateBoothZone(quietRefusals);
  const { mutateAsync: update } = useUpdateBoothZone(quietRefusals);

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (values: typeof form.values) => {
      setErrorCode(null);
      const data = toZoneRequest(values);
      const targetId = zone?.id ?? createdZoneId;
      const saved = targetId
        ? await update({ boothZoneId: targetId, data })
        : await create({ eventId, data });
      setCreatedZoneId(saved.id);
      await layout.save(saved.id);
      await queryClient.invalidateQueries({
        queryKey: getListBoothZonesQueryKey(eventId),
      });
      notifySuccess(
        zone ? t("kp.manage.zone_updated") : t("kp.manage.zone_created"),
      );
      onClose();
    },
    (error) => {
      const status = getApiErrorStatus(error);
      if (status !== undefined && REFUSED_SAVE_STATUSES.includes(status)) {
        setErrorCode(getApiErrorCode(error) ?? "error.internal");
      }
    },
  );

  const title = zone
    ? t("kp.manage.booth_zones_edit")
    : t("kp.manage.booth_zones_add");

  return (
    <ManageEntityModal
      opened={opened}
      onClose={onClose}
      title={title}
      isSaving={isSaving}
      isSubmitDisabled={!form.values.name.trim() || !form.isValid()}
      submitLabel={title}
      onSubmit={form.onSubmit((values) => {
        void save(values);
      })}
    >
      <TextInput
        label={t("kp.manage.zone_name")}
        disabled={isSaving}
        {...form.getInputProps("name")}
      />
      <Textarea
        label={t("kp.manage.zone_description")}
        disabled={isSaving}
        {...form.getInputProps("description")}
      />
      <ColorInput
        label={t("kp.manage.zone_color")}
        disabled={isSaving}
        {...form.getInputProps("color")}
      />
      <Group grow>
        <NumberInput
          allowDecimal={false}
          label={t("kp.manage.zone_capacity")}
          min={0}
          disabled={isSaving}
          {...form.getInputProps("capacity")}
        />
        <NumberInput
          label={t("kp.manage.zone_booth_size")}
          min={0}
          decimalScale={2}
          disabled={isSaving}
          {...form.getInputProps("boothSize")}
        />
      </Group>
      <NumberInput
        label={t("kp.manage.zone_base_price")}
        min={0}
        decimalScale={2}
        fixedDecimalScale
        disabled={isSaving}
        {...form.getInputProps("basePrice")}
      />

      <Divider label={t("kp.manage.zone_layout_title")} />
      <Textarea
        label={t("kp.manage.zone_layout_description")}
        disabled={isSaving}
        {...form.getInputProps("layoutDescription")}
      />
      <BoothZoneLayoutField layout={layout} disabled={isSaving} />

      <Divider label={t("kp.manage.zone_included_services")} />
      <IncludedServicesEditor
        form={form}
        services={services}
        disabled={isSaving}
        addLabel={t("kp.manage.zone_included_add")}
        removeLabel={t("kp.manage.zone_included_remove")}
        emptyLabel={t("kp.manage.zone_included_empty")}
      />
      {errorCode !== null ? <ErrorAlert>{t(errorCode)}</ErrorAlert> : null}
    </ManageEntityModal>
  );
};

export default BoothZoneFormModal;
