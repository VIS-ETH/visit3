import { Select } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchCompanies } from "../../orval/generated/company/company";

const SEARCH_DEBOUNCE_MS = 300;
const SEARCH_PAGE_SIZE = 20;

interface CompanyOption {
  value: string;
  label: string;
}

interface CompanySelectProps {
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
  selectedOption?: CompanyOption | null;
}

const CompanySelect = ({
  value,
  onChange,
  disabled,
  selectedOption,
}: CompanySelectProps) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);

  const { data } = useSearchCompanies({
    query: debouncedSearch.trim() || undefined,
    page: 1,
    page_size: SEARCH_PAGE_SIZE,
  });

  const options: CompanyOption[] = (data?.items ?? []).map((company) => ({
    value: company.id,
    label: company.name,
  }));

  if (
    selectedOption &&
    !options.some((option) => option.value === selectedOption.value)
  ) {
    options.unshift(selectedOption);
  }

  return (
    <Select
      clearable
      data={options}
      disabled={disabled}
      label={t("user_management.edit.company")}
      nothingFoundMessage={t("user_management.edit.company_empty")}
      onChange={onChange}
      onSearchChange={setSearch}
      placeholder={t("user_management.edit.company_placeholder")}
      searchable
      value={value}
    />
  );
};

export default CompanySelect;
