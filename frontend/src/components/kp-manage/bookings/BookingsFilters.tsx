import { Checkbox, Group, MultiSelect, Select, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { BOOKING_STATUS_ORDER } from "../../../utils/booking-status";
import { BOOKING_STATUS_LABEL_KEYS } from "../../../utils/kp-utils";
import ServiceFilterSelect from "../../staff-bookings/ServiceFilterSelect";
import { ALL_STATUSES, type BookingFilters } from "./use-booking-filters";

const BookingsFilters = ({ filters }: { filters: BookingFilters }) => {
  const { t } = useTranslation();

  return (
    <Group align="flex-end" gap="sm">
      <TextInput
        flex={1}
        leftSection={<IconSearch size={16} />}
        maw={320}
        onChange={(event) => filters.setSearch(event.currentTarget.value)}
        placeholder={t("kp.manage.bookings_search_placeholder")}
        value={filters.search}
      />
      <Select
        allowDeselect={false}
        data={[
          {
            value: ALL_STATUSES,
            label: t("kp.manage.bookings_filter_status_all"),
          },
          ...BOOKING_STATUS_ORDER.map((status) => ({
            value: status,
            label: t(BOOKING_STATUS_LABEL_KEYS[status]),
          })),
        ]}
        label={t("kp.manage.bookings_filter_status")}
        onChange={(value) => filters.setStatusFilter(value ?? ALL_STATUSES)}
        value={filters.statusFilter}
        w={200}
      />
      {filters.zoneOptions.length > 0 ? (
        <MultiSelect
          clearable
          searchable
          data={filters.zoneOptions}
          label={t("kp.manage.bookings_filter_zones")}
          onChange={filters.setZoneFilter}
          placeholder={t("kp.manage.bookings_filter_zones_all")}
          value={filters.zoneFilter}
          w={220}
        />
      ) : null}
      {filters.bookedServices.length > 0 ? (
        <ServiceFilterSelect
          label={t("kp.manage.bookings_filter_services")}
          onChange={filters.setServiceFilter}
          placeholder={t("kp.manage.bookings_filter_services_all")}
          services={filters.bookedServices}
          value={filters.serviceFilter}
          w={280}
        />
      ) : null}
      <Checkbox
        checked={filters.incompleteOnly}
        label={t("kp.manage.bookings_filter_incomplete")}
        onChange={(event) =>
          filters.setIncompleteOnly(event.currentTarget.checked)
        }
        pb={8}
      />
      <Checkbox
        checked={filters.onlyChanges}
        label={t("changes.only_changes")}
        onChange={(event) =>
          filters.setOnlyChanges(event.currentTarget.checked)
        }
        pb={8}
      />
    </Group>
  );
};

export default BookingsFilters;
