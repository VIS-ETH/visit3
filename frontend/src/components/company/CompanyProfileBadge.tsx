import { Badge } from "@mantine/core";
import { IconAlertTriangle, IconCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

interface CompanyProfileBadgeProps {
  complete: boolean;
}

const CompanyProfileBadge = ({ complete }: CompanyProfileBadgeProps) => {
  const { t } = useTranslation();

  return (
    <Badge
      color={complete ? "green" : "orange"}
      variant="light"
      size="lg"
      leftSection={
        complete ? <IconCheck size={14} /> : <IconAlertTriangle size={14} />
      }
    >
      {complete
        ? t("company_profile_form.complete")
        : t("company_profile_form.incomplete")}
    </Badge>
  );
};

export default CompanyProfileBadge;
