import {
  Badge,
  Group,
  Loader,
  ScrollArea,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { MailCampaignAudienceResponse } from "../../orval/generated/fastAPI.schemas";

const TABLE_HEIGHT = 320;
const TABLE_MIN_WIDTH = 560;
const VIA_COLUMN_WIDTH = 160;

interface MailCampaignRecipientsProps {
  audience: MailCampaignAudienceResponse | undefined;
  isFetching: boolean;
}

const MailCampaignRecipients = ({
  audience,
  isFetching,
}: MailCampaignRecipientsProps) => {
  const { t } = useTranslation();

  return (
    <div>
      <Group justify="space-between" align="center" mb="xs">
        <Title order={5}>{t("mail_campaigns.recipients.title")}</Title>
        <Group gap="xs">
          {isFetching ? <Loader size="xs" /> : null}
          {audience ? (
            <Text size="sm" data-testid="mail-campaign-recipient-count">
              {t("mail_campaigns.recipients.summary", {
                count: audience.recipient_count,
                skipped: audience.skipped_count,
              })}
            </Text>
          ) : null}
        </Group>
      </Group>
      {audience?.recipients.length === 0 ? (
        <Text c="dimmed" size="sm">
          {t("mail_campaigns.recipients.empty")}
        </Text>
      ) : null}
      {audience && audience.recipients.length > 0 ? (
        <ScrollArea.Autosize mah={TABLE_HEIGHT}>
          <Table.ScrollContainer minWidth={TABLE_MIN_WIDTH}>
            <Table striped highlightOnHover verticalSpacing={4} fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("mail_campaigns.recipients.company")}</Table.Th>
                  <Table.Th>{t("mail_campaigns.recipients.address")}</Table.Th>
                  <Table.Th miw={VIA_COLUMN_WIDTH}>
                    {t("mail_campaigns.recipients.via")}
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {audience.recipients.map((recipient) => (
                  <Table.Tr key={recipient.company_id}>
                    <Table.Td>
                      <Group gap={6} wrap="nowrap">
                        <Text size="sm">{recipient.company_name}</Text>
                        {recipient.manually_included ? (
                          <Badge size="xs" variant="outline">
                            {t("mail_campaigns.recipients.manual")}
                          </Badge>
                        ) : null}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text
                        size="sm"
                        c={recipient.skip_reason ? "dimmed" : undefined}
                        td={
                          recipient.skip_reason === "DUPLICATE_ADDRESS"
                            ? "line-through"
                            : undefined
                        }
                      >
                        {recipient.email ?? "-"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {recipient.skip_reason ? (
                        <Badge size="sm" variant="light" color="orange">
                          {t(`mail_campaigns.skip.${recipient.skip_reason}`)}
                        </Badge>
                      ) : recipient.source ? (
                        <Badge
                          size="sm"
                          variant="light"
                          color={
                            recipient.source === "CONTACT" ? "green" : "blue"
                          }
                        >
                          {t(`mail_campaigns.source.${recipient.source}`)}
                        </Badge>
                      ) : null}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </ScrollArea.Autosize>
      ) : null}
    </div>
  );
};
export default MailCampaignRecipients;
