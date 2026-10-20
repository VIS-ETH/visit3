import { Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { MailCampaignSummaryResponse } from "../../orval/generated/fastAPI.schemas";
import { formatZurichDateTime } from "../../utils/mail-campaign";
import { MailCampaignStatusBadge } from "./MailCampaignStatusBadge";

interface MailCampaignListProps {
  campaigns: MailCampaignSummaryResponse[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

const campaignDate = (campaign: MailCampaignSummaryResponse) =>
  campaign.finished_at ??
  campaign.started_at ??
  campaign.scheduled_at ??
  campaign.updated_at;

const MailCampaignList = ({
  campaigns,
  activeId,
  onSelect,
  onCreate,
}: MailCampaignListProps) => {
  const { t, i18n } = useTranslation();

  return (
    <Paper withBorder p="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" wrap="nowrap">
          <Title order={4}>{t("mail_campaigns.list_title")}</Title>
          <Button
            size="compact-sm"
            leftSection={<IconPlus size={14} />}
            variant={activeId === null ? "light" : "default"}
            onClick={onCreate}
          >
            {t("mail_campaigns.new")}
          </Button>
        </Group>
        {campaigns.length === 0 ? (
          <Text c="dimmed" size="sm">
            {t("mail_campaigns.empty")}
          </Text>
        ) : null}
        {campaigns.map((campaign) => (
          <Button
            key={campaign.id}
            variant={campaign.id === activeId ? "light" : "subtle"}
            justify="space-between"
            h="auto"
            py="xs"
            onClick={() => onSelect(campaign.id)}
            rightSection={
              <MailCampaignStatusBadge size="xs" status={campaign.status} />
            }
            styles={{ label: { flex: 1, minWidth: 0 } }}
          >
            <Stack gap={0} align="flex-start" style={{ minWidth: 0 }}>
              <Text size="sm" truncate maw="100%">
                {campaign.name}
              </Text>
              <Text size="xs" c="dimmed">
                {formatZurichDateTime(campaignDate(campaign), i18n.language)}
              </Text>
            </Stack>
          </Button>
        ))}
      </Stack>
    </Paper>
  );
};
export default MailCampaignList;
