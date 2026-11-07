import type { ReactNode } from "react";
import { Alert } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

const ErrorAlert = ({ children }: { children?: ReactNode }) => {
  const { t } = useTranslation();
  return (
    <Alert icon={<IconAlertCircle />} color="red">
      {children ?? t("error.load_failed")}
    </Alert>
  );
};

export default ErrorAlert;
