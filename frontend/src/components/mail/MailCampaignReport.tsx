import {
  Button,
  Group,
  Loader,
  Paper,
  ScrollArea,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCopy, IconRefresh } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  MailCampaignRecipientStatus,
  MailCampaignStatus,
  type MailCampaignRecipientResult,
  type MailCampaignResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getGetMailCampaignQueryKey,
  getListMailCampaignsQueryKey,
  useDuplicateMailCampaign,
  useRetryMailCampaign,
} from "../../orval/generated/mail-campaigns/mail-campaigns";
import { formatZurichDateTime } from "../../utils/mail-campaign";
import {
  MailCampaignRecipientStatusBadge,
  MailCampaignStatusBadge,
} from "./MailCampaignStatusBadge";

const TABLE_HEIGHT = 480;
const TABLE_MIN_WIDTH = 720;
const STATUS_COLUMN_WIDTH = 140;
const TIME_COLUMN_WIDTH = 150;
const FILTERS = ["all", "failed", "skipped"] as const;
type Filter = (typeof FILTERS)[number];

const FILTERED_STATUS: Record<Exclude<Filter, "all">, string> = {
  failed: MailCampaignRecipientStatus.FAILED,
  skipped: MailCampaignRecipientStatus.SKIPPED,
};

const isFilter = (value: string): value is Filter =>
  FILTERS.some((filter) => filter === value);

interface MailCampaignReportProps {
  campaign: MailCampaignResponse;
  onDuplicated: (campaign: MailCampaignResponse) => void;
}

const MailCampaignReport = ({
  campaign,
  onDuplicated,
}: MailCampaignReportProps) => {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<Filter>("all");

  const refresh = async (updated: MailCampaignResponse) => {
    queryClient.setQueryData(getGetMailCampaignQueryKey(updated.id), updated);
    await queryClient.invalidateQueries({
      queryKey: getListMailCampaignsQueryKey(),
    });
  };

  const { mutate: retry, isPending: isRetrying } = useRetryMailCampaign({
    mutation: {
      onSuccess: async (updated) => {
        await refresh(updated);
        notifications.show({
          color: "green",
          message: t("mail_campaigns.retry_success"),
        });
      },
    },
  });
  const { mutate: duplicate, isPending: isDuplicating } =
    useDuplicateMailCampaign({
      mutation: {
        onSuccess: async (copy) => {
          await refresh(copy);
          onDuplicated(copy);
        },
      },
    });

  const recipients = campaign.recipients.filter(
    (recipient) =>
      filter === "all" || recipient.status === FILTERED_STATUS[filter],
  );
  const note = (recipient: MailCampaignRecipientResult) =>
    recipient.error
      ? t(`mail_campaigns.failure.${recipient.error}`)
      : recipient.skip_reason
        ? t(`mail_campaigns.skip.${recipient.skip_reason}`)
        : recipient.source
          ? t(`mail_campaigns.source.${recipient.source}`)
          : null;
  const stats = [
    ["sent", campaign.counts.sent],
    ["failed", campaign.counts.failed],
    ["skipped", campaign.counts.skipped],
    ["pending", campaign.counts.pending],
  ] as const;
  const isSending = campaign.status === MailCampaignStatus.SENDING;

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="lg">
        <Group justify="space-between" align="center" wrap="nowrap">
          <div style={{ minWidth: 0 }}>
            <Title order={4} lineClamp={1}>
              {campaign.name}
            </Title>
            <Text size="sm" c="dimmed">
              {campaign.event_name}
              {" · "}
              {formatZurichDateTime(
                campaign.finished_at ?? campaign.started_at,
                i18n.language,
              )}
            </Text>
          </div>
          <Group gap="xs" wrap="nowrap">
            {isSending ? <Loader size="xs" /> : null}
            <MailCampaignStatusBadge status={campaign.status} />
          </Group>
        </Group>

        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          {stats.map(([key, value]) => (
            <Paper key={key} withBorder p="sm" radius="md">
              <Text size="xs" c="dimmed">
                {t(`mail_campaigns.counts.${key}`)}
              </Text>
              <Text fw={700} size="xl" data-testid={`mail-campaign-${key}`}>
                {value}
              </Text>
            </Paper>
          ))}
        </SimpleGrid>

        <div>
          <Text size="sm" fw={600}>
            {campaign.subject_de}
          </Text>
          {campaign.subject_en ? (
            <Text size="sm" c="dimmed">
              {campaign.subject_en}
            </Text>
          ) : null}
        </div>

        <Group justify="space-between" gap="sm">
          <SegmentedControl
            size="xs"
            value={filter}
            onChange={(value) => {
              if (isFilter(value)) setFilter(value);
            }}
            data={FILTERS.map((value) => ({
              value,
              label: t(`mail_campaigns.filter.${value}`),
            }))}
          />
          <Group gap="sm">
            {campaign.status === MailCampaignStatus.PARTIALLY_FAILED ? (
              <Button
                color="red"
                variant="light"
                leftSection={<IconRefresh size={16} />}
                loading={isRetrying}
                onClick={() => retry({ campaignId: campaign.id })}
              >
                {t("mail_campaigns.retry", { count: campaign.counts.failed })}
              </Button>
            ) : null}
            <Button
              variant="default"
              leftSection={<IconCopy size={16} />}
              loading={isDuplicating}
              onClick={() => duplicate({ campaignId: campaign.id })}
            >
              {t("mail_campaigns.duplicate")}
            </Button>
          </Group>
        </Group>

        <ScrollArea.Autosize mah={TABLE_HEIGHT}>
          <Table.ScrollContainer minWidth={TABLE_MIN_WIDTH}>
            <Table striped verticalSpacing={4} fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("mail_campaigns.recipients.company")}</Table.Th>
                  <Table.Th>{t("mail_campaigns.recipients.address")}</Table.Th>
                  <Table.Th miw={STATUS_COLUMN_WIDTH}>
                    {t("mail_campaigns.log.status")}
                  </Table.Th>
                  <Table.Th miw={TIME_COLUMN_WIDTH}>
                    {t("mail_campaigns.log.time")}
                  </Table.Th>
                  <Table.Th>{t("mail_campaigns.log.note")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {recipients.map((recipient) => (
                  <Table.Tr key={recipient.id}>
                    <Table.Td>{recipient.company_name}</Table.Td>
                    <Table.Td>{recipient.email ?? "-"}</Table.Td>
                    <Table.Td>
                      <MailCampaignRecipientStatusBadge
                        status={recipient.status}
                      />
                    </Table.Td>
                    <Table.Td style={{ whiteSpace: "nowrap" }}>
                      {formatZurichDateTime(
                        recipient.sent_at ?? recipient.last_attempt_at,
                        i18n.language,
                      ) ?? "-"}
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {note(recipient)}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </ScrollArea.Autosize>
        {recipients.length === 0 ? (
          <Text c="dimmed" size="sm">
            {t("mail_campaigns.log.empty")}
          </Text>
        ) : null}
      </Stack>
    </Paper>
  );
};
export default MailCampaignReport;
