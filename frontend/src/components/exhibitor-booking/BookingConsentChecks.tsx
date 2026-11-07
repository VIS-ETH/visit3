import { Anchor, Checkbox, Text } from "@mantine/core";
import type { ReactNode, RefObject } from "react";
import { useTranslation } from "react-i18next";

interface BookingConsentChecksProps {
  termsUrl: string | null;
  agbAccepted: boolean;
  bindingAccepted: boolean;
  onAgbChange: (accepted: boolean) => void;
  onBindingChange: (accepted: boolean) => void;
  highlight: boolean;
  agbCheckboxRef?: RefObject<HTMLInputElement | null>;
  bindingCheckboxRef?: RefObject<HTMLInputElement | null>;
}

const BookingConsentChecks = ({
  termsUrl,
  agbAccepted,
  bindingAccepted,
  onAgbChange,
  onBindingChange,
  highlight,
  agbCheckboxRef,
  bindingCheckboxRef,
}: BookingConsentChecksProps) => {
  const { t } = useTranslation();

  const requiredLabel = (content: ReactNode, showError: boolean) => (
    <Text
      component="span"
      size="sm"
      lh={1.45}
      c={showError ? "red" : undefined}
    >
      {content}
      <Text component="span" c="red" fw={700} ml={4} aria-hidden>
        *
      </Text>
    </Text>
  );

  const agbLabelContent = termsUrl ? (
    <>
      {t("kp.booking.confirm_agb_prefix")}{" "}
      <Anchor href={termsUrl} target="_blank" rel="noopener noreferrer">
        {t("kp.booking.confirm_agb_link")}
      </Anchor>
    </>
  ) : (
    t("kp.booking.confirm_agb_checkbox")
  );

  return (
    <>
      <Checkbox
        ref={agbCheckboxRef}
        checked={agbAccepted}
        onChange={(e) => onAgbChange(e.currentTarget.checked)}
        label={requiredLabel(agbLabelContent, highlight && !agbAccepted)}
      />
      <Checkbox
        ref={bindingCheckboxRef}
        checked={bindingAccepted}
        onChange={(e) => onBindingChange(e.currentTarget.checked)}
        label={requiredLabel(
          t("kp.booking.confirm_binding_checkbox"),
          highlight && !bindingAccepted,
        )}
      />
    </>
  );
};

export default BookingConsentChecks;
