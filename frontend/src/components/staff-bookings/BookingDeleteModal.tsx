import { Checkbox, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import BookingActionModal from "./BookingActionModal";

const BookingDeleteModal = ({
  onClose,
  onConfirm,
  opened,
  requiresForce,
}: {
  onClose: () => void;
  onConfirm: (force: boolean) => Promise<unknown>;
  opened: boolean;
  requiresForce: boolean;
}) => {
  const { t } = useTranslation();
  const [force, setForce] = useState(false);

  useEffect(() => {
    if (!opened) setForce(false);
  }, [opened]);

  return (
    <BookingActionModal
      color="red"
      isSubmitDisabled={requiresForce && !force}
      onClose={onClose}
      onSubmit={() => onConfirm(force)}
      opened={opened}
      submitLabel={t("kp.manage.booking_delete_submit")}
      title={t("kp.manage.booking_delete_title")}
    >
      {(isSubmitting) => (
        <>
          <Text size="sm">{t("kp.manage.booking_delete_body")}</Text>
          {requiresForce ? (
            <Checkbox
              checked={force}
              disabled={isSubmitting}
              label={t("kp.manage.booking_delete_force")}
              onChange={(event) => setForce(event.currentTarget.checked)}
            />
          ) : null}
        </>
      )}
    </BookingActionModal>
  );
};

export default BookingDeleteModal;
