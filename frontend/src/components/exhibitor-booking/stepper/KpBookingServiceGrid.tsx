import { SimpleGrid, Text } from "@mantine/core";
import type { ServiceResponse } from "../../../orval/generated/fastAPI.schemas";
import {
  blockingServiceName,
  clampServiceQuantity,
} from "../../../utils/kp-service-quantity";
import ErrorAlert from "../../ErrorAlert";
import PageLoader from "../../PageLoader";
import type {
  DraftBookingRequirementValue,
  DraftBookingService,
} from "../KpBookingSummaryStep";
import KpBookingServiceCard from "./KpBookingServiceCard";

export interface ServiceStepProps {
  services: ServiceResponse[];
  allServices: ServiceResponse[];
  includedQuantities: Map<string, number>;
  excludedBy: Map<string, string>;
  selectedServices: DraftBookingService[];
  onChangeServices: (services: DraftBookingService[]) => void;
  isLoading: boolean;
  isError: boolean;
}

const KpBookingServiceGrid = ({
  services,
  allServices,
  includedQuantities,
  excludedBy,
  selectedServices,
  onChangeServices,
  emptyLabel,
  isLoading,
  isError,
}: ServiceStepProps & { emptyLabel: string }) => {
  const includedFor = (serviceId: string) =>
    includedQuantities.get(serviceId) ?? 0;
  const selectedServiceById = new Map(
    selectedServices.map((service) => [service.serviceId, service]),
  );
  const serviceNameById = new Map(
    allServices.map((service) => [service.id, service.name]),
  );

  const withoutPackageContents = (
    items: DraftBookingService[],
    service: ServiceResponse,
  ) =>
    (service.included_services ?? []).reduce((current, content) => {
      const included = includedFor(content.service_id);
      return current.flatMap((item) => {
        if (item.serviceId !== content.service_id) return [item];
        const quantity = Math.max(
          item.quantity - content.included_quantity,
          included - content.included_quantity,
          0,
        );
        return quantity > 0 ? [{ ...item, quantity }] : [];
      });
    }, items);

  const updateQuantity = (service: ServiceResponse, quantity: number) => {
    const nextQuantity = clampServiceQuantity(
      service,
      includedFor(service.id),
      quantity,
    );
    const previousQuantity = selectedServiceById.get(service.id)?.quantity ?? 0;
    let next = selectedServices.filter((item) => item.serviceId !== service.id);
    if (previousQuantity > 0 && nextQuantity === 0) {
      next = withoutPackageContents(next, service);
    }
    if (nextQuantity > 0) {
      const current = selectedServiceById.get(service.id);
      next.push({
        serviceId: service.id,
        quantity: nextQuantity,
        requirements: current?.requirements ?? {},
      });
    }
    onChangeServices(next);
  };

  const updateRequirement = (
    serviceId: string,
    requirementId: string,
    value: DraftBookingRequirementValue,
  ) => {
    onChangeServices(
      selectedServices.map((service) =>
        service.serviceId === serviceId
          ? {
              ...service,
              requirements: {
                ...(service.requirements ?? {}),
                [requirementId]: {
                  ...(service.requirements?.[requirementId] ?? {}),
                  ...value,
                },
              },
            }
          : service,
      ),
    );
  };

  if (isLoading) return <PageLoader />;

  if (isError) return <ErrorAlert />;

  if (services.length === 0) {
    return (
      <Text c="dimmed" size="sm" mt="md">
        {emptyLabel}
      </Text>
    );
  }

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" mt="md">
      {services.map((service, index) => (
        <KpBookingServiceCard
          key={service.id}
          service={service}
          selectedService={selectedServiceById.get(service.id)}
          included={includedFor(service.id)}
          blockedBy={blockingServiceName(service, excludedBy)}
          contents={(service.included_services ?? [])
            .map(
              (content) =>
                `${content.included_quantity}× ${
                  serviceNameById.get(content.service_id) ?? ""
                }`,
            )
            .join(", ")}
          showVatHint={index === 0}
          onQuantityChange={(quantity) => updateQuantity(service, quantity)}
          onRequirementChange={(requirementId, value) =>
            updateRequirement(service.id, requirementId, value)
          }
        />
      ))}
    </SimpleGrid>
  );
};

export default KpBookingServiceGrid;
