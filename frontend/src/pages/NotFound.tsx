import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import StatusPage from "../components/StatusPage";

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <StatusPage
      code="404"
      title={t("not_found.title")}
      description={t("not_found.description")}
      icon={<IconAlertCircle size={34} />}
      iconColor="orange"
      homeLabel={t("nav.home")}
    />
  );
}
