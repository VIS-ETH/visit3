import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import StatusPage from "../components/StatusPage";

export default function NotAllowed() {
  const { t } = useTranslation();

  return (
    <StatusPage
      code="403"
      title={t("not_allowed.title")}
      description={t("not_allowed.description")}
      icon={<IconAlertCircle size={34} />}
      iconColor="red"
      homeLabel={t("nav.home")}
    />
  );
}
