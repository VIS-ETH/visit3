import {
  Badge,
  CloseButton,
  Group,
  SegmentedControl,
  Select,
  Stack,
  TextInput,
} from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  CompanyFilter,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";

const filterLabelKeys: Record<CompanyFilter, string> = {
  [CompanyFilter.all]: "company_management.filters.all",
  [CompanyFilter.unconfirmed]: "company_management.filters.unconfirmed",
  [CompanyFilter.new]: "company_management.filters.new",
};

interface CompanyFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  filter: CompanyFilter;
  onFilterChange: (value: CompanyFilter) => void;
  companyFilterLabel: string | null;
  onClearCompany: () => void;
  events: KpResponse[];
  eventId: string | null;
  onEventChange: (value: string | null) => void;
  isLoadingEvents: boolean;
}

const CompanyFilters = ({
  search,
  onSearchChange,
  filter,
  onFilterChange,
  companyFilterLabel,
  onClearCompany,
  events,
  eventId,
  onEventChange,
  isLoadingEvents,
}: CompanyFiltersProps) => {
  const { t } = useTranslation();

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="flex-end">
        <TextInput
          flex={1}
          leftSection={<IconSearch size={16} />}
          maw={360}
          onChange={(event) => onSearchChange(event.currentTarget.value)}
          placeholder={t("company_management.search_placeholder")}
          value={search}
        />
        <SegmentedControl
          data={Object.entries(filterLabelKeys).map(([value, labelKey]) => ({
            value,
            label: t(labelKey),
          }))}
          onChange={(value) => onFilterChange(value as CompanyFilter)}
          value={filter}
        />
        <Select
          label={t("kp.bookings_overview.event")}
          data={events.map((event) => ({ value: event.id, label: event.name }))}
          value={eventId}
          onChange={onEventChange}
          allowDeselect={false}
          disabled={isLoadingEvents}
          w={{ base: "100%", sm: 280 }}
        />
      </Group>
      {companyFilterLabel !== null ? (
        <Group>
          <Badge
            rightSection={
              <CloseButton
                aria-label={t("company_management.clear_company_filter")}
                onClick={onClearCompany}
                size="xs"
              />
            }
            size="lg"
            tt="none"
            variant="light"
          >
            {t("company_management.company_filter", {
              company: companyFilterLabel,
            })}
          </Badge>
        </Group>
      ) : null}
    </Stack>
  );
};

export default CompanyFilters;
