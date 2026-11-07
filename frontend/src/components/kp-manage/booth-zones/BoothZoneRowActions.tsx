import { ActionIcon, Group } from "@mantine/core";
import {
  IconArrowDown,
  IconArrowUp,
  IconEdit,
  IconTrash,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

const BoothZoneRowActions = ({
  canMoveUp,
  canMoveDown,
  isBusy,
  onMove,
  onEdit,
  onDelete,
}: {
  canMoveUp: boolean;
  canMoveDown: boolean;
  isBusy: boolean;
  onMove: (offset: number) => void;
  onEdit: () => void;
  onDelete: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <Group gap="xs" wrap="nowrap">
      <ActionIcon
        variant="subtle"
        aria-label={t("kp.manage.zone_move_up")}
        disabled={!canMoveUp || isBusy}
        onClick={() => onMove(-1)}
      >
        <IconArrowUp size={16} />
      </ActionIcon>
      <ActionIcon
        variant="subtle"
        aria-label={t("kp.manage.zone_move_down")}
        disabled={!canMoveDown || isBusy}
        onClick={() => onMove(1)}
      >
        <IconArrowDown size={16} />
      </ActionIcon>
      <ActionIcon
        variant="subtle"
        onClick={onEdit}
        aria-label={t("kp.manage.booth_zones_edit")}
      >
        <IconEdit size={16} />
      </ActionIcon>
      <ActionIcon
        color="red"
        variant="subtle"
        aria-label={t("kp.manage.zone_confirm_delete")}
        disabled={isBusy}
        onClick={() => {
          if (confirm(t("kp.manage.zone_confirm_delete"))) onDelete();
        }}
      >
        <IconTrash size={16} />
      </ActionIcon>
    </Group>
  );
};

export default BoothZoneRowActions;
