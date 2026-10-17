import { MultiSelect, type MultiSelectProps } from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
  SERVICE_CATEGORY_LABEL_KEYS,
  servicesByCategory,
  type FilterService,
} from "./service-filter";

type ServiceFilterSelectProps = Omit<MultiSelectProps, "data"> & {
  services: FilterService[];
};

const ServiceFilterSelect = ({
  services,
  ...props
}: ServiceFilterSelectProps) => {
  const { t } = useTranslation();
  const data = servicesByCategory(services).map((group) => ({
    group: t(SERVICE_CATEGORY_LABEL_KEYS[group.category].group),
    items: [
      {
        value: group.category,
        label: t(SERVICE_CATEGORY_LABEL_KEYS[group.category].any),
      },
      ...group.services.map((service) => ({
        value: service.id,
        label: service.name,
      })),
    ],
  }));

  return <MultiSelect clearable searchable data={data} {...props} />;
};
export default ServiceFilterSelect;
