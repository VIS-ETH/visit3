import { Badge } from "@mantine/core";
import { IconCheck, IconProgressCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

const RequirementsBadge = ({
  completed,
  total,
}: {
  completed: number;
  total: number;
}) => {
  const { t } = useTranslation();
  const isComplete = completed === total;

  return (
    <Badge
      color={isComplete ? "green" : "yellow"}
      leftSection={
        isComplete ? <IconCheck size={12} /> : <IconProgressCheck size={12} />
      }
      variant="light"
    >
      {total
        ? t("kp.booking_manage.requirements_completed_count", {
            completed,
            total,
          })
        : t("kp.booking_manage.no_requirements")}
    </Badge>
  );
};

export default RequirementsBadge;
