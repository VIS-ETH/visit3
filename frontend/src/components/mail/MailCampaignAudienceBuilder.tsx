import { Chip, Group, MultiSelect, Stack, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";
import { MailCampaignSegment } from "../../orval/generated/fastAPI.schemas";
import { useListBoothZones } from "../../orval/generated/kp/kp";
import { useListMailCampaignCompanies } from "../../orval/generated/mail-campaigns/mail-campaigns";
import type { MailCampaignFormValues } from "../../schemas/mailCampaignSchema";
import { MAIL_CAMPAIGN_SEGMENTS } from "../../utils/mail-campaign";

interface MailCampaignAudienceBuilderProps {
  form: UseFormReturnType<MailCampaignFormValues>;
  disabled: boolean;
}

const isSegment = (value: string): value is MailCampaignSegment =>
  MAIL_CAMPAIGN_SEGMENTS.some((segment) => segment === value);

const MailCampaignAudienceBuilder = ({
  form,
  disabled,
}: MailCampaignAudienceBuilderProps) => {
  const { t } = useTranslation();
  const { eventId, includeCompanyIds, excludeCompanyIds } = form.values;
  const { data: zones } = useListBoothZones(eventId, {
    query: { enabled: eventId.length > 0 },
  });
  const { data: companies } = useListMailCampaignCompanies();

  const companyOptions = (companies ?? []).map((company) => ({
    value: company.id,
    label: company.name,
  }));
  const without = (ids: string[]) =>
    companyOptions.filter((option) => !ids.includes(option.value));

  return (
    <Stack gap="sm">
      <div>
        <Text size="sm" fw={500}>
          {t("mail_campaigns.audience.segments")}
        </Text>
        <Text size="xs" c="dimmed" mb={6}>
          {t("mail_campaigns.audience.segments_hint")}
        </Text>
        <Chip.Group
          multiple
          value={form.values.segments}
          onChange={(values) =>
            form.setFieldValue("segments", values.filter(isSegment))
          }
        >
          <Group gap="xs">
            {MAIL_CAMPAIGN_SEGMENTS.map((segment) => (
              <Chip key={segment} value={segment} size="sm" disabled={disabled}>
                {t(`mail_campaigns.segment.${segment}`)}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
      </div>
      <MultiSelect
        label={t("mail_campaigns.audience.zones")}
        description={t("mail_campaigns.audience.zones_hint")}
        placeholder={t("mail_campaigns.audience.zones_placeholder")}
        data={(zones ?? []).map((zone) => ({
          value: zone.id,
          label: zone.name,
        }))}
        clearable
        searchable
        disabled={disabled || !eventId}
        {...form.getInputProps("boothZoneIds")}
      />
      <MultiSelect
        label={t("mail_campaigns.audience.include")}
        placeholder={t("mail_campaigns.audience.company_placeholder")}
        data={without(excludeCompanyIds)}
        clearable
        searchable
        disabled={disabled}
        {...form.getInputProps("includeCompanyIds")}
      />
      <MultiSelect
        label={t("mail_campaigns.audience.exclude")}
        placeholder={t("mail_campaigns.audience.company_placeholder")}
        data={without(includeCompanyIds)}
        clearable
        searchable
        disabled={disabled}
        {...form.getInputProps("excludeCompanyIds")}
      />
    </Stack>
  );
};
export default MailCampaignAudienceBuilder;
