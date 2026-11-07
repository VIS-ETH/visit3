import { MultiSelect, Stack, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";
import type { ServiceResponse } from "../../orval/generated/fastAPI.schemas";
import IncludedServicesEditor from "../kp-manage/IncludedServicesEditor";
import type { ServiceFormValues } from "./service-form-values";

const ServiceRelationsFields = ({
  form,
  otherServices,
  disabled,
}: {
  form: UseFormReturnType<ServiceFormValues>;
  otherServices: ServiceResponse[];
  disabled: boolean;
}) => {
  const { t } = useTranslation();
  const excludedOptions = otherServices
    .filter(
      (service) =>
        !form.values.includedServices.some(
          (included) => included.serviceId === service.id,
        ),
    )
    .map((service) => ({ value: service.id, label: service.name }));

  return (
    <Stack gap="sm">
      <Text c="dimmed" size="sm">
        {t("kp.manage.service_contains_description")}
      </Text>
      <IncludedServicesEditor
        form={form}
        services={otherServices}
        excludedServiceIds={form.values.excludedServiceIds}
        disabled={disabled}
        addLabel={t("kp.manage.service_contains_add")}
        removeLabel={t("kp.manage.service_contains_remove")}
      />
      <MultiSelect
        clearable
        data={excludedOptions}
        description={t("kp.manage.service_excludes_description")}
        disabled={disabled}
        label={t("kp.manage.service_excludes")}
        searchable
        {...form.getInputProps("excludedServiceIds")}
      />
    </Stack>
  );
};

export default ServiceRelationsFields;
