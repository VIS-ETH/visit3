import { Badge } from "@mantine/core";
import { useTranslation } from "react-i18next";

const BookingNewAdditionsBadge = () => {
  const { t } = useTranslation();

  return (
    <Badge color="orange" size="sm" variant="dot">
      {t("kp.manage.booking_new_additions")}
    </Badge>
  );
};

export default BookingNewAdditionsBadge;
