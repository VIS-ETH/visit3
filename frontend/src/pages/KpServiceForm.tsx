import { Button, Divider, Group, Paper, Stack, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import ServiceDetailsFields from "../components/service-form/ServiceDetailsFields";
import ServiceRelationsFields from "../components/service-form/ServiceRelationsFields";
import ServiceRequirementsEditor from "../components/service-form/ServiceRequirementsEditor";
import {
  emptyServiceFormValues,
  toServiceFormValues,
  toServiceRequest,
} from "../components/service-form/service-form-values";
import { useServiceImage } from "../components/service-form/use-service-image";
import {
  getListServicesQueryKey,
  useCreateService,
  useListServices,
  useUpdateService,
} from "../orval/generated/kp/kp";
import { useAsyncAction } from "../hooks/use-async-action";
import { serviceSchema } from "../schemas/kpSchema";
import { notifySuccess } from "../utils/notify";
import { useTranslatedForm } from "../utils/translator";

const KpServiceForm = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id: eventId, serviceId } = useParams<{
    id: string;
    serviceId?: string;
  }>();
  const isEditing = Boolean(serviceId);
  const [createdServiceId, setCreatedServiceId] = useState<string | null>(null);
  const servicesPath = `/kp/${eventId}?tab=services`;
  const { data: services, isLoading, isError } = useListServices(eventId ?? "");
  const service = services?.find((item) => item.id === serviceId);
  const image = useServiceImage();
  const initialisedServiceIdRef = useRef<string | null>(null);

  const form = useTranslatedForm<typeof serviceSchema>(serviceSchema, {
    initialValues: emptyServiceFormValues,
  });

  const { mutateAsync: create } = useCreateService();
  const { mutateAsync: update } = useUpdateService();

  useEffect(() => {
    if (!service || initialisedServiceIdRef.current === service.id) return;
    initialisedServiceIdRef.current = service.id;
    form.setValues(toServiceFormValues(service));
    form.resetDirty();
    form.clearErrors();
    image.reset();
  }, [service, form, image]);

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (values: typeof form.values) => {
      if (!eventId) return;
      const data = toServiceRequest(values);
      const targetId = serviceId ?? createdServiceId;
      const saved = targetId
        ? await update({ serviceId: targetId, data })
        : await create({ eventId, data });
      setCreatedServiceId(saved.id);
      await image.save(saved.id, Boolean(service?.image_url));
      await queryClient.invalidateQueries({
        queryKey: getListServicesQueryKey(eventId),
      });
      notifySuccess(
        isEditing
          ? t("kp.manage.service_updated")
          : t("kp.manage.service_created"),
      );
      void navigate(servicesPath);
    },
  );

  if (!eventId) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <ErrorAlert>{t("kp.manage.not_found")}</ErrorAlert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <BackButton to={servicesPath} />
        <PageLoader />
      </Stack>
    );
  }

  if (isError || (isEditing && !service)) {
    return (
      <Stack gap="md">
        <BackButton to={servicesPath} />
        <ErrorAlert>
          {isError ? undefined : t("kp.manage.service_not_found")}
        </ErrorAlert>
      </Stack>
    );
  }

  const otherServices = (services ?? []).filter(
    (item) => item.id !== serviceId && item.id !== createdServiceId,
  );

  return (
    <Stack gap="md">
      <BackButton to={servicesPath} />
      <Group justify="space-between" align="flex-start">
        <Title order={2}>
          {isEditing
            ? t("kp.manage.services_edit")
            : t("kp.manage.services_add")}
        </Title>
      </Group>

      <form
        id="kp-service-form"
        onSubmit={form.onSubmit((values) => {
          void save(values);
        })}
      >
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <ServiceDetailsFields
              form={form}
              disabled={isSaving}
              onImageUrlChange={image.changeUrl}
              onImageFileChange={image.chooseFile}
            />
            <Divider label={t("kp.manage.service_contains")} />
            <ServiceRelationsFields
              form={form}
              otherServices={otherServices}
              disabled={isSaving}
            />
            <Divider label={t("kp.manage.service_requirements")} />
            <ServiceRequirementsEditor form={form} disabled={isSaving} />
            <Group justify="flex-end" mt="sm">
              <Button
                component={Link}
                to={servicesPath}
                variant="default"
                disabled={isSaving}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                loading={isSaving}
                disabled={!form.values.name.trim() || !form.isValid()}
              >
                {t("kp.manage.save")}
              </Button>
            </Group>
          </Stack>
        </Paper>
      </form>
    </Stack>
  );
};

export default KpServiceForm;
