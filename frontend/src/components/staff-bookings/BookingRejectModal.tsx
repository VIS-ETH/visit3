import { Text, Textarea } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import BookingActionModal from "./BookingActionModal";

const REJECTION_REASON_MIN_LENGTH = 10;
const REJECTION_REASON_MAX_LENGTH = 1000;

const BookingRejectModal = ({
  onClose,
  onConfirm,
  opened,
}: {
  onClose: () => void;
  onConfirm: (reason: string) => Promise<unknown>;
  opened: boolean;
}) => {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!opened) setReason("");
  }, [opened]);

  const trimmedReason = reason.trim();
  const isTooShort =
    trimmedReason.length > 0 &&
    trimmedReason.length < REJECTION_REASON_MIN_LENGTH;
  const isTooLong = trimmedReason.length > REJECTION_REASON_MAX_LENGTH;
  const isValid = !isTooShort && !isTooLong && trimmedReason.length > 0;

  const error = isTooShort
    ? t("kp.manage.booking_reject_reason_too_short", {
        min: REJECTION_REASON_MIN_LENGTH,
      })
    : isTooLong
      ? t("kp.manage.booking_reject_reason_too_long", {
          max: REJECTION_REASON_MAX_LENGTH,
        })
      : undefined;

  return (
    <BookingActionModal
      color="red"
      isSubmitDisabled={!isValid}
      onClose={onClose}
      onSubmit={() => onConfirm(trimmedReason)}
      opened={opened}
      submitLabel={t("kp.manage.booking_reject_submit")}
      title={t("kp.manage.booking_reject_title")}
    >
      {(isSubmitting) => (
        <>
          <Text size="sm">{t("kp.manage.booking_reject_body")}</Text>
          <Textarea
            autosize
            disabled={isSubmitting}
            error={error}
            label={t("kp.manage.booking_reject_reason")}
            minRows={4}
            onChange={(event) => setReason(event.currentTarget.value)}
            placeholder={t("kp.manage.booking_reject_reason_placeholder")}
            value={reason}
          />
          <Text c="dimmed" size="xs" ta="right">
            {t("kp.manage.booking_reject_reason_counter", {
              length: trimmedReason.length,
              max: REJECTION_REASON_MAX_LENGTH,
            })}
          </Text>
        </>
      )}
    </BookingActionModal>
  );
};

export default BookingRejectModal;
