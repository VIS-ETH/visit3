import { ActionIcon, Group, Tooltip } from "@mantine/core";
import {
  IconCircleCheck,
  IconId,
  IconMail,
  IconTrash,
  IconUsers,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type { CompanyListResult } from "../../orval/generated/fastAPI.schemas";

interface CompanyRowActionsProps {
  company: CompanyListResult;
  canDelete: boolean;
  canMail: boolean;
  isConfirming: boolean;
  onConfirm: () => void;
  onShowMembers: () => void;
  onMail: () => void;
  onDelete: () => void;
}

const RowAction = ({
  label,
  color,
  disabled,
  onClick,
  children,
}: {
  label: string;
  color?: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) => (
  <Tooltip label={label} withArrow>
    <ActionIcon
      aria-label={label}
      color={color}
      disabled={disabled}
      onClick={onClick}
      variant="light"
    >
      {children}
    </ActionIcon>
  </Tooltip>
);

const CompanyRowActions = ({
  company,
  canDelete,
  canMail,
  isConfirming,
  onConfirm,
  onShowMembers,
  onMail,
  onDelete,
}: CompanyRowActionsProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <Group gap="xs" wrap="nowrap">
      {company.confirmed_at === null ? (
        <RowAction
          color="green"
          disabled={isConfirming}
          label={t("company_management.confirm")}
          onClick={onConfirm}
        >
          <IconCircleCheck size={16} />
        </RowAction>
      ) : null}
      <RowAction
        label={t("company_management.view_users")}
        onClick={onShowMembers}
      >
        <IconUsers size={16} />
      </RowAction>
      <RowAction
        label={t("company_management.edit_profile")}
        onClick={() =>
          void navigate(`/company-management/${company.id}/profile`)
        }
      >
        <IconId size={16} />
      </RowAction>
      {canMail ? (
        <RowAction label={t("company_management.send_mail")} onClick={onMail}>
          <IconMail size={16} />
        </RowAction>
      ) : null}
      {canDelete ? (
        <RowAction
          color="red"
          label={t("company_management.delete")}
          onClick={onDelete}
        >
          <IconTrash size={16} />
        </RowAction>
      ) : null}
    </Group>
  );
};

export default CompanyRowActions;
