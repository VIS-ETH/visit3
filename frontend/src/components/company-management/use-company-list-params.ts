import { useSearchParams } from "react-router";
import { CompanyFilter } from "../../orval/generated/fastAPI.schemas";

const isCompanyFilter = (value: string | null): value is CompanyFilter =>
  value !== null && Object.values<string>(CompanyFilter).includes(value);

export const useCompanyListParams = (onChange: () => void) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawFilter = searchParams.get("filter");
  const filter = isCompanyFilter(rawFilter) ? rawFilter : CompanyFilter.all;
  const companyId = searchParams.get("company");

  const updateParam = (key: string, value: string | null) => {
    onChange();
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  };

  const setFilter = (value: CompanyFilter) =>
    updateParam("filter", value === CompanyFilter.all ? null : value);
  const clearCompany = () => updateParam("company", null);

  return { filter, setFilter, companyId, clearCompany } as const;
};
