import {
  Alert,
  Center,
  Grid,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import MailCampaignEditor from "../components/mail/MailCampaignEditor";
import MailCampaignList from "../components/mail/MailCampaignList";
import MailCampaignReport from "../components/mail/MailCampaignReport";
import {
  MailCampaignStatus,
  type MailCampaignResponse,
} from "../orval/generated/fastAPI.schemas";
import { useListKps } from "../orval/generated/kp/kp";
import {
  useGetMailCampaign,
  useListMailCampaigns,
} from "../orval/generated/mail-campaigns/mail-campaigns";
import { isEditableCampaign } from "../utils/mail-campaign";

const SENDING_REFRESH_MS = 2000;
const NEW_CAMPAIGN = "new";

const MailCampaigns = () => {
  const { t } = useTranslation();
  const {
    data: campaigns,
    isLoading,
    isError,
  } = useListMailCampaigns({
    query: {
      refetchInterval: (query) =>
        query.state.data?.some(
          (item) => item.status === MailCampaignStatus.SENDING,
        )
          ? SENDING_REFRESH_MS
          : false,
    },
  });
  const { data: events } = useListKps();
  const [selected, setSelected] = useState<string | null>(null);

  const activeId =
    selected === NEW_CAMPAIGN ? null : (selected ?? campaigns?.[0]?.id ?? null);
  const { data: campaign, isLoading: isLoadingCampaign } = useGetMailCampaign(
    activeId ?? "",
    {
      query: {
        enabled: activeId !== null,
        refetchInterval: (query) =>
          query.state.data?.status === MailCampaignStatus.SENDING
            ? SENDING_REFRESH_MS
            : false,
      },
    },
  );
  const defaultEventId = events?.[0]?.id ?? null;
  const showCampaign = (next: MailCampaignResponse) => setSelected(next.id);

  const loading = (
    <Paper withBorder p="lg" radius="md">
      <Center py="xl">
        <Loader />
      </Center>
    </Paper>
  );

  const content = () => {
    if (!events) return loading;
    if (activeId === null) {
      return (
        <MailCampaignEditor
          key={NEW_CAMPAIGN}
          campaign={null}
          events={events}
          defaultEventId={defaultEventId}
          onSaved={showCampaign}
          onDeleted={() => setSelected(null)}
        />
      );
    }
    if (isLoadingCampaign || campaign?.id !== activeId) return loading;
    if (isEditableCampaign(campaign.status)) {
      return (
        <MailCampaignEditor
          key={`${campaign.id}-${campaign.updated_at}`}
          campaign={campaign}
          events={events}
          defaultEventId={defaultEventId}
          onSaved={showCampaign}
          onDeleted={() => setSelected(null)}
        />
      );
    }
    return (
      <MailCampaignReport campaign={campaign} onDuplicated={showCampaign} />
    );
  };

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <div>
        <Title order={2}>{t("mail_campaigns.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("mail_campaigns.description")}
        </Text>
      </div>

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("mail_campaigns.error")}
        </Alert>
      ) : null}

      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : null}

      {campaigns ? (
        <Grid gap="md" align="flex-start">
          <Grid.Col span={{ base: 12, md: 4, lg: 3 }}>
            <MailCampaignList
              campaigns={campaigns}
              activeId={activeId}
              onSelect={setSelected}
              onCreate={() => setSelected(NEW_CAMPAIGN)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 8, lg: 9 }}>{content()}</Grid.Col>
        </Grid>
      ) : null}
    </Stack>
  );
};
export default MailCampaigns;
