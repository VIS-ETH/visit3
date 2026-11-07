import { ActionIcon, Badge, Group, Text, TextInput } from "@mantine/core";
import { IconCheck, IconPencil, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { CompanyListResult } from "../../orval/generated/fastAPI.schemas";
import BookingNewAdditionsBadge from "../staff-bookings/BookingNewAdditionsBadge";

interface CompanyNameCellProps {
  company: CompanyListResult;
  isEditing: boolean;
  isSaving: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: (name: string) => void;
}

const CompanyNameCell = ({
  company,
  isEditing,
  isSaving,
  onEdit,
  onCancel,
  onSave,
}: CompanyNameCellProps) => {
  const { t } = useTranslation();
  const [name, setName] = useState(company.name);
  const trimmed = name.trim();

  const save = () => {
    if (trimmed !== "") onSave(trimmed);
  };

  if (isEditing) {
    return (
      <Group gap="xs" wrap="nowrap">
        <TextInput
          aria-label={t("company_management.rename")}
          autoFocus
          disabled={isSaving}
          onChange={(event) => setName(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              save();
            } else if (event.key === "Escape") {
              event.preventDefault();
              onCancel();
            }
          }}
          value={name}
        />
        <ActionIcon
          aria-label={t("company_management.rename_save")}
          color="green"
          disabled={trimmed === ""}
          loading={isSaving}
          onClick={save}
          variant="light"
        >
          <IconCheck size={16} />
        </ActionIcon>
        <ActionIcon
          aria-label={t("company_management.rename_cancel")}
          disabled={isSaving}
          onClick={onCancel}
          variant="subtle"
        >
          <IconX size={16} />
        </ActionIcon>
      </Group>
    );
  }

  return (
    <Group gap="xs" wrap="nowrap">
      <Text>{company.name}</Text>
      {company.confirmed_at === null ? (
        <Badge color="yellow" size="sm" variant="light">
          {t("company_management.unconfirmed")}
        </Badge>
      ) : null}
      {company.new_members_count ? <BookingNewAdditionsBadge /> : null}
      <ActionIcon
        aria-label={t("company_management.rename")}
        onClick={() => {
          setName(company.name);
          onEdit();
        }}
        variant="subtle"
      >
        <IconPencil size={16} />
      </ActionIcon>
    </Group>
  );
};

export default CompanyNameCell;
