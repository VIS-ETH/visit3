import {
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../../hooks/use-async-action";
import {
  KpServiceCategory,
  type BookingResponse,
  type BookingServiceResponse,
  type ServiceResponse,
} from "../../../orval/generated/fastAPI.schemas";
import {
  useAddBookingServices,
  useListAvailableServices,
} from "../../../orval/generated/kp/kp";
import {
  blockingServiceName,
  excludedByService,
  servicesOfCategory,
  withPackageInclusions,
} from "../../../utils/kp-service-quantity";
import { notifySuccess } from "../../../utils/notify";
import ErrorAlert from "../../ErrorAlert";
import PageLoader from "../../PageLoader";
import AddServiceCard from "./AddServiceCard";
import AddServicesConfirmModal from "./AddServicesConfirmModal";

const AddServicesForm = ({
  bookingId,
  bookingServices,
  editable,
  eventId,
  onAdded,
  vatRatePercent,
}: {
  bookingId: string;
  bookingServices: BookingServiceResponse[];
  editable: boolean;
  eventId: string;
  onAdded: (booking: BookingResponse, serviceIds: string[]) => Promise<void>;
  vatRatePercent: number;
}) => {
  const { t } = useTranslation();
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const {
    data: availableServices,
    isLoading,
    isError,
  } = useListAvailableServices(eventId);
  const { mutateAsync: addServices } = useAddBookingServices();
  const bookingServiceByServiceId = useMemo(
    () => new Map(bookingServices.map((item) => [item.service_id, item])),
    [bookingServices],
  );
  const services = useMemo(() => availableServices ?? [], [availableServices]);
  const bookedQuantityOf = (serviceId: string) =>
    bookingServiceByServiceId.get(serviceId)?.quantity ?? 0;
  const selectedServices = services
    .map((service) => ({
      service,
      quantity:
        (quantities[service.id] ?? bookedQuantityOf(service.id)) -
        bookedQuantityOf(service.id),
    }))
    .filter((item) => item.quantity > 0);
  const packageIncluded = withPackageInclusions(
    new Map(),
    services,
    bookingServices.map((item) => ({
      serviceId: item.service_id,
      quantity: item.quantity,
    })),
  );
  const zoneIncluded = new Map(
    bookingServices.map((item) => [
      item.service_id,
      Math.max(
        item.included_quantity - (packageIncluded.get(item.service_id) ?? 0),
        0,
      ),
    ]),
  );
  const excludedBy = excludedByService(
    services,
    services.map((service) => ({
      serviceId: service.id,
      quantity: quantities[service.id] ?? bookedQuantityOf(service.id),
    })),
    zoneIncluded,
  );
  const serviceNameById = new Map(
    services.map((service) => [service.id, service.name]),
  );
  const contentsOf = (service: ServiceResponse) =>
    (service.included_services ?? [])
      .map(
        (content) =>
          `${content.included_quantity}× ${
            serviceNameById.get(content.service_id) ?? ""
          }`,
      )
      .join(", ");

  const { run: submit, isRunning: isSubmitting } = useAsyncAction(async () => {
    const payload = selectedServices.map((item) => ({
      service_id: item.service.id,
      quantity: item.quantity,
    }));
    if (!payload.length) return;
    const updated = await addServices({
      bookingId,
      data: { services: payload },
    });
    await onAdded(
      updated,
      payload.map((item) => item.service_id),
    );
    setQuantities({});
    setConfirmOpen(false);
    notifySuccess(t("kp.booking_manage.services_added"));
  });

  const renderCategory = (category: KpServiceCategory, emptyLabel: string) => {
    if (isError) return <ErrorAlert />;
    if (isLoading) return <PageLoader />;
    const categoryServices = servicesOfCategory(services, category);
    if (categoryServices.length === 0) {
      return (
        <Text c="dimmed" size="sm">
          {emptyLabel}
        </Text>
      );
    }
    return (
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
        {categoryServices.map((service) => {
          const bookingService = bookingServiceByServiceId.get(service.id);
          const bookedQuantity = bookingService?.quantity ?? 0;
          return (
            <AddServiceCard
              blockedBy={blockingServiceName(service, excludedBy)}
              bookedQuantity={bookedQuantity}
              contents={contentsOf(service)}
              editable={editable && !isSubmitting}
              includedQuantity={bookingService?.included_quantity ?? 0}
              key={service.id}
              onQuantityChange={(quantity) =>
                setQuantities((current) => ({
                  ...current,
                  [service.id]: quantity,
                }))
              }
              quantity={quantities[service.id] ?? bookedQuantity}
              service={service}
            />
          );
        })}
      </SimpleGrid>
    );
  };

  return (
    <Card withBorder radius="md" p="lg">
      <AddServicesConfirmModal
        isSubmitting={isSubmitting}
        onClose={() => setConfirmOpen(false)}
        onSubmit={() => {
          void submit();
        }}
        opened={confirmOpen}
        selectedServices={selectedServices}
        vatRatePercent={vatRatePercent}
      />
      <Stack gap="md">
        <div>
          <Title order={4}>{t("kp.booking_manage.add_services_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.booking_manage.add_services_description")}
          </Text>
        </div>

        <Tabs defaultValue="services" keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab value="services">
              {t("kp.booking_manage.add_services_tab_services")}
            </Tabs.Tab>
            <Tabs.Tab value="booth_elements">
              {t("kp.booking_manage.add_services_tab_booth_elements")}
            </Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="services">
            {renderCategory(
              KpServiceCategory.SERVICE,
              t("kp.booking.services_none_available"),
            )}
          </Tabs.Panel>
          <Tabs.Panel value="booth_elements">
            {renderCategory(
              KpServiceCategory.BOOTH_ELEMENT,
              t("kp.booking.booth_none_available"),
            )}
          </Tabs.Panel>
        </Tabs>

        <Group justify="flex-end">
          <Button
            leftSection={<IconPlus size={16} />}
            disabled={!editable || selectedServices.length === 0}
            loading={isSubmitting}
            onClick={() => setConfirmOpen(true)}
          >
            {t("kp.booking_manage.add_services_submit")}
          </Button>
        </Group>
      </Stack>
    </Card>
  );
};

export default AddServicesForm;
