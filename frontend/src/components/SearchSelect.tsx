import { Select, type ComboboxItem, type SelectProps } from "@mantine/core";
import { useState, type SyntheticEvent } from "react";

type SearchSelectProps = Omit<
  SelectProps,
  "data" | "searchable" | "searchValue" | "onSearchChange" | "allowDeselect"
> & {
  data: ComboboxItem[];
};

const selectText = (event: SyntheticEvent<HTMLInputElement>) =>
  event.currentTarget.select();

const SearchSelect = ({
  data,
  onOptionSubmit,
  ...props
}: SearchSelectProps) => {
  const [search, setSearch] = useState("");

  return (
    <Select
      {...props}
      data={data}
      searchable
      allowDeselect={false}
      searchValue={search}
      onSearchChange={setSearch}
      onFocus={selectText}
      onClick={selectText}
      onOptionSubmit={(value) => {
        setSearch(data.find((item) => item.value === value)?.label ?? "");
        onOptionSubmit?.(value);
      }}
    />
  );
};

export default SearchSelect;
