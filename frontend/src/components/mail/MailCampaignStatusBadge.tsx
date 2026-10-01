import { Badge, type BadgeProps } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type {
  MailCampaignRecipientStatus,
  MailCampaignStatus,
} from "../../orval/generated/fastAPI.schemas";
import { MAIL_CAMPAIGN_STATUS_COLORS } from "../../utils/mail-campaign";

const RECIPIENT_STATUS_COLORS: Record<MailCampaignRecipientStatus, string> = {
  PENDING: "gray",
  SENDING: "yellow",
  SENT: "green",
  FAILED: "red",
  SKIPPED: "orange",
};

export const MailCampaignStatusBadge = ({
  status,
  ...props
}: { status: MailCampaignStatus } & BadgeProps) => {
  const { t } = useTranslation();
  return (
    <Badge
      variant="light"
      color={MAIL_CAMPAIGN_STATUS_COLORS[status]}
      {...props}
    >
      {t(`mail_campaigns.status.${status}`)}
    </Badge>
  );
};

export const MailCampaignRecipientStatusBadge = ({
  status,
}: {
  status: MailCampaignRecipientStatus;
}) => {
  const { t } = useTranslation();
  return (
    <Badge variant="light" color={RECIPIENT_STATUS_COLORS[status]}>
      {t(`mail_campaigns.recipient_status.${status}`)}
    </Badge>
  );
};
