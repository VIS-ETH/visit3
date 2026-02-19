import type { ReactNode } from "react";
import { Box, Button, Loader, Paper, ScrollArea, Stack, TextInput } from "@mantine/core";

export type SearchDropdownItem = {
  id?: string;
  name: string;
};

type SearchDropdownProps = {
  label: string;
  placeholder: string;
  withAsterisk?: boolean;
  error?: ReactNode;
  isLoading: boolean;
  visible: boolean;
  items: SearchDropdownItem[];
  query: string;
  createLabel: string;
  isCreating: boolean;
  onQueryChange: (value: string) => void;
  onSelect: (item: SearchDropdownItem) => void;
  onCreate: () => void;
};

const SearchDropdown = ({
  label,
  placeholder,
  withAsterisk,
  error,
  isLoading,
  visible,
  items,
  query,
  createLabel,
  isCreating,
  onQueryChange,
  onSelect,
  onCreate,
}: SearchDropdownProps) => {
  return (
    <Box pos="relative">
      <TextInput
        label={label}
        placeholder={placeholder}
        withAsterisk={withAsterisk}
        value={query}
        onChange={(event) => onQueryChange(event.currentTarget.value)}
        error={error}
        rightSection={isLoading || isCreating ? <Loader size="xs" /> : null}
      />

      {visible && (
        <Paper
          withBorder
          radius="sm"
          p={0}
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 20,
            overflow: "hidden",
          }}
        >
          <ScrollArea.Autosize mah={220} type="auto">
            <Stack gap={0}>
              {items.length > 0 ? (
                items.map((item) => (
                  <Button
                    key={item.id}
                    variant="subtle"
                    justify="flex-start"
                    fullWidth
                    radius={0}
                    onClick={() => onSelect(item)}
                  >
                    {item.name}
                  </Button>
                ))
              ) : (
                <Button
                  variant="light"
                  justify="flex-start"
                  fullWidth
                  radius={0}
                  onClick={onCreate}
                  disabled={isCreating}
                >
                  {`${createLabel}: ${query.trim()}`}
                </Button>
              )}
            </Stack>
          </ScrollArea.Autosize>
        </Paper>
      )}
    </Box>
  );
};

export default SearchDropdown;
