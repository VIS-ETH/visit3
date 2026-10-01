import {
  Alert,
  Button,
  Divider,
  Group,
  Loader,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCalendarTime,
  IconClock,
  IconMailForward,
  IconSend,
  IconTrash,
} from "@tabler/icons-react";
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { AxiosRequestConfig } from "axios";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  MailCampaignStatus,
  type KpResponse,
  type MailCampaignAudienceRequest,
  type MailCampaignRenderRequest,
  type MailCampaignResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getGetMailCampaignQueryKey,
  getListMailCampaignsQueryKey,
  previewMailCampaignAudience,
  renderMailCampaign,
  useCreateMailCampaign,
  useDeleteMailCampaign,
  useListMailCampaignVariables,
  useScheduleMailCampaign,
  useSendMailCampaign,
  useTestSendMailCampaign,
  useUnscheduleMailCampaign,
  useUpdateMailCampaign,
} from "../../orval/generated/mail-campaigns/mail-campaigns";
import { mailCampaignSchema } from "../../schemas/mailCampaignSchema";
import {
  emptyMailCampaignValues,
  formatZurichDateTime,
  isFutureZurichInput,
  mailCampaignValues,
  nextFullHourInput,
  toMailCampaignAudienceRequest,
  toMailCampaignRenderRequest,
  toMailCampaignRequest,
  zurichDateTimeInput,
} from "../../utils/mail-campaign";
import { getInvalidMailTemplateField } from "../../utils/mail-template";
import { useTranslatedForm } from "../../utils/translator";
import MailCampaignAudienceBuilder from "./MailCampaignAudienceBuilder";
import MailCampaignConfirmModal from "./MailCampaignConfirmModal";
import MailCampaignContent from "./MailCampaignContent";
import MailCampaignRecipients from "./MailCampaignRecipients";
import { MailCampaignStatusBadge } from "./MailCampaignStatusBadge";
import MailTemplatePreview from "./MailTemplatePreview";

const AUDIENCE_DELAY_MS = 400;
const RENDER_DELAY_MS = 600;
const QUIET_VALIDATION: AxiosRequestConfig = { quietStatuses: [400, 422] };

type ConfirmAction = "send" | "schedule" | "delete";

interface MailCampaignEditorProps {
  campaign: MailCampaignResponse | null;
  events: KpResponse[];
  defaultEventId: string | null;
  onSaved: (campaign: MailCampaignResponse) => void;
  onDeleted: () => void;
}

const MailCampaignEditor = ({
  campaign,
  events,
  defaultEventId,
  onSaved,
  onDeleted,
}: MailCampaignEditorProps) => {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const form = useTranslatedForm(mailCampaignSchema, {
    initialValues: campaign
      ? mailCampaignValues(campaign)
      : emptyMailCampaignValues(defaultEventId),
  });
  const values = form.values;
  const [action, setAction] = useState<ConfirmAction | null>(null);
  const [confirmCount, setConfirmCount] = useState<number | null>(null);
  const [scheduleValue, setScheduleValue] = useState(() =>
    campaign?.scheduled_at
      ? zurichDateTimeInput(new Date(campaign.scheduled_at))
      : nextFullHourInput(),
  );
  const [sampleCompanyId, setSampleCompanyId] = useState<string | null>(null);
  const [isWorking, setIsWorking] = useState(false);

  const { data: variables } = useListMailCampaignVariables();

  const audienceRequest = JSON.stringify(toMailCampaignAudienceRequest(values));
  const [debouncedAudience] = useDebouncedValue(
    audienceRequest,
    AUDIENCE_DELAY_MS,
  );
  const audienceQuery = useQuery({
    queryKey: ["mail-campaign-audience", debouncedAudience],
    queryFn: () =>
      previewMailCampaignAudience(
        JSON.parse(debouncedAudience) as MailCampaignAudienceRequest,
      ),
    enabled: values.eventId.length > 0,
    placeholderData: keepPreviousData,
  });
  const audience = values.eventId ? audienceQuery.data : undefined;
  const sampleOptions = (audience?.recipients ?? [])
    .filter((recipient) => recipient.email && !recipient.skip_reason)
    .map((recipient) => ({
      value: recipient.company_id,
      label: recipient.company_name,
    }));
  const activeSample = sampleOptions.some(
    (option) => option.value === sampleCompanyId,
  )
    ? sampleCompanyId
    : (sampleOptions[0]?.value ?? null);

  const renderRequest = JSON.stringify(
    toMailCampaignRenderRequest(values, activeSample),
  );
  const [debouncedRender] = useDebouncedValue(renderRequest, RENDER_DELAY_MS);
  const englishComplete =
    values.subjectEn.trim().length > 0 === values.bodyEn.trim().length > 0;
  const canRender =
    values.eventId.length > 0 &&
    values.subjectDe.trim().length > 0 &&
    values.bodyDe.trim().length > 0 &&
    englishComplete;
  const renderQuery = useQuery({
    queryKey: ["mail-campaign-render", debouncedRender],
    queryFn: () =>
      renderMailCampaign(
        JSON.parse(debouncedRender) as MailCampaignRenderRequest,
        QUIET_VALIDATION,
      ),
    enabled: canRender,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const invalidPreview = getInvalidMailTemplateField(renderQuery.error);

  const { mutateAsync: create } = useCreateMailCampaign();
  const { mutateAsync: update } = useUpdateMailCampaign();
  const { mutateAsync: remove } = useDeleteMailCampaign();
  const { mutateAsync: send } = useSendMailCampaign();
  const { mutateAsync: schedule } = useScheduleMailCampaign();
  const { mutateAsync: unschedule, isPending: isUnscheduling } =
    useUnscheduleMailCampaign();
  const { mutate: testSend, isPending: isTestSending } =
    useTestSendMailCampaign({
      mutation: {
        onSuccess: () =>
          notifications.show({
            color: "green",
            message: t("mail_campaigns.test_send_success"),
          }),
      },
    });

  const refresh = async (saved?: MailCampaignResponse) => {
    await queryClient.invalidateQueries({
      queryKey: getListMailCampaignsQueryKey(),
    });
    if (saved) {
      queryClient.setQueryData(getGetMailCampaignQueryKey(saved.id), saved);
    }
  };

  const showInvalidTemplate = (error: unknown) => {
    const invalid = getInvalidMailTemplateField(error);
    if (!invalid) return;
    form.setFieldError(
      invalid.field,
      invalid.variable
        ? t("mail_templates.invalid_variable", { variable: invalid.variable })
        : t("mail_templates.invalid_field"),
    );
  };

  const persist = async () => {
    const data = toMailCampaignRequest(form.getValues());
    try {
      return campaign
        ? await update({ campaignId: campaign.id, data })
        : await create({ data });
    } catch (error) {
      showInvalidTemplate(error);
      throw error;
    }
  };

  const run = async (
    task: () => Promise<MailCampaignResponse>,
    message: string,
  ) => {
    setIsWorking(true);
    try {
      const saved = await task();
      await refresh(saved);
      setAction(null);
      notifications.show({ color: "green", message });
      onSaved(saved);
    } catch {
      return;
    } finally {
      setIsWorking(false);
    }
  };

  const handleSave = () => run(persist, t("mail_campaigns.save_success"));

  const openConfirm = (next: ConfirmAction) => {
    if (next !== "delete" && form.validate().hasErrors) return;
    setAction(next);
    if (next !== "send") return;
    setConfirmCount(null);
    void previewMailCampaignAudience(
      toMailCampaignAudienceRequest(form.getValues()),
    )
      .then((result) => setConfirmCount(result.recipient_count))
      .catch(() => setAction(null));
  };

  const persistThen = async (
    step: (saved: MailCampaignResponse) => Promise<MailCampaignResponse>,
  ) => {
    const saved = await persist();
    try {
      return await step(saved);
    } catch (error) {
      if (!campaign) {
        await refresh(saved);
        onSaved(saved);
      }
      throw error;
    }
  };

  const confirmSend = () =>
    run(
      () => persistThen((saved) => send({ campaignId: saved.id })),
      t("mail_campaigns.send_success"),
    );

  const confirmSchedule = () =>
    run(
      () =>
        persistThen((saved) =>
          schedule({
            campaignId: saved.id,
            data: { scheduled_at: scheduleValue },
          }),
        ),
      t("mail_campaigns.schedule_success"),
    );

  const cancelSchedule = async () => {
    if (!campaign) return;
    const saved = await unschedule({ campaignId: campaign.id });
    await refresh(saved);
    onSaved(saved);
  };

  const confirmDelete = async () => {
    if (!campaign) return;
    setIsWorking(true);
    try {
      await remove({ campaignId: campaign.id });
      await refresh();
      setAction(null);
      notifications.show({
        color: "green",
        message: t("mail_campaigns.delete_success"),
      });
      onDeleted();
    } catch {
      return;
    } finally {
      setIsWorking(false);
    }
  };

  const scheduleIsValid = isFutureZurichInput(scheduleValue);
  const scheduledAt = formatZurichDateTime(
    campaign?.scheduled_at,
    i18n.language,
  );

  return (
    <Paper withBorder p="lg" radius="md">
      <form onSubmit={form.onSubmit(() => void handleSave())}>
        <Stack gap="lg">
          <Group justify="space-between" align="center" wrap="nowrap">
            <Title order={4} style={{ minWidth: 0 }} lineClamp={1}>
              {campaign?.name ?? t("mail_campaigns.new_title")}
            </Title>
            {campaign ? (
              <MailCampaignStatusBadge status={campaign.status} />
            ) : null}
          </Group>

          {campaign?.status === MailCampaignStatus.SCHEDULED ? (
            <Alert
              color="blue"
              icon={<IconClock />}
              title={t("mail_campaigns.scheduled_for", { date: scheduledAt })}
            >
              <Group justify="space-between" gap="xs">
                <Text size="sm">{t("mail_campaigns.scheduled_hint")}</Text>
                <Button
                  size="xs"
                  variant="default"
                  loading={isUnscheduling}
                  onClick={() => void cancelSchedule()}
                >
                  {t("mail_campaigns.unschedule")}
                </Button>
              </Group>
            </Alert>
          ) : null}

          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label={t("mail_campaigns.name")}
              disabled={isWorking}
              {...form.getInputProps("name")}
            />
            <Select
              label={t("mail_campaigns.event")}
              data={events.map((event) => ({
                value: event.id,
                label: event.name,
              }))}
              allowDeselect={false}
              disabled={isWorking}
              {...form.getInputProps("eventId")}
              onChange={(value) => {
                form.setFieldValue("eventId", value ?? "");
                form.setFieldValue("boothZoneIds", []);
              }}
            />
          </SimpleGrid>

          <Divider label={t("mail_campaigns.section.audience")} />
          <MailCampaignAudienceBuilder form={form} disabled={isWorking} />
          <MailCampaignRecipients
            audience={audience}
            isFetching={audienceQuery.isFetching}
          />

          <Divider label={t("mail_campaigns.section.content")} />
          <MailCampaignContent
            form={form}
            variables={variables ?? []}
            disabled={isWorking}
          />

          <Divider label={t("mail_campaigns.section.preview")} />
          <Group justify="space-between" align="flex-end" gap="sm">
            <Select
              label={t("mail_campaigns.preview_company")}
              placeholder={t("mail_campaigns.preview_sample")}
              data={sampleOptions}
              value={activeSample}
              onChange={setSampleCompanyId}
              searchable
              allowDeselect={false}
              style={{ flex: 1, minWidth: 200 }}
            />
            <Button
              variant="default"
              leftSection={<IconMailForward size={16} />}
              loading={isTestSending}
              disabled={!canRender}
              onClick={() =>
                testSend({
                  data: toMailCampaignRenderRequest(values, activeSample),
                })
              }
            >
              {t("mail_campaigns.test_send")}
            </Button>
          </Group>
          {invalidPreview ? (
            <Alert color="red" icon={<IconAlertCircle />}>
              {invalidPreview.variable
                ? t("mail_templates.invalid_variable", {
                    variable: invalidPreview.variable,
                  })
                : t("mail_templates.invalid_field")}
            </Alert>
          ) : null}
          {renderQuery.isFetching && !renderQuery.data ? (
            <Loader size="sm" />
          ) : (
            <MailTemplatePreview preview={renderQuery.data ?? null} />
          )}

          <Divider />
          <Group justify="space-between" gap="sm">
            <div>
              {campaign ? (
                <Button
                  color="red"
                  variant="subtle"
                  leftSection={<IconTrash size={16} />}
                  disabled={isWorking}
                  onClick={() => openConfirm("delete")}
                >
                  {t("mail_campaigns.delete")}
                </Button>
              ) : null}
            </div>
            <Group gap="sm" justify="flex-end">
              <Button type="submit" variant="default" loading={isWorking}>
                {t("mail_campaigns.save")}
              </Button>
              <Button
                variant="default"
                leftSection={<IconCalendarTime size={16} />}
                disabled={isWorking}
                onClick={() => openConfirm("schedule")}
              >
                {t("mail_campaigns.schedule")}
              </Button>
              <Button
                leftSection={<IconSend size={16} />}
                disabled={isWorking}
                onClick={() => openConfirm("send")}
              >
                {t("mail_campaigns.send_now")}
              </Button>
            </Group>
          </Group>
        </Stack>
      </form>

      <MailCampaignConfirmModal
        opened={action === "send"}
        title={t("mail_campaigns.send_modal.title")}
        confirmLabel={t("mail_campaigns.send_modal.confirm")}
        confirmDisabled={!confirmCount}
        isPending={isWorking}
        onConfirm={() => void confirmSend()}
        onClose={() => setAction(null)}
      >
        {confirmCount === null ? (
          <Loader size="sm" />
        ) : (
          <Text data-testid="mail-campaign-send-count">
            {confirmCount > 0
              ? t("mail_campaigns.send_modal.message", { count: confirmCount })
              : t("mail_campaigns.send_modal.nobody")}
          </Text>
        )}
      </MailCampaignConfirmModal>

      <MailCampaignConfirmModal
        opened={action === "schedule"}
        title={t("mail_campaigns.schedule_modal.title")}
        confirmLabel={t("mail_campaigns.schedule_modal.confirm")}
        confirmDisabled={!scheduleIsValid}
        isPending={isWorking}
        onConfirm={() => void confirmSchedule()}
        onClose={() => setAction(null)}
      >
        <TextInput
          type="datetime-local"
          label={t("mail_campaigns.schedule_modal.label")}
          description={t("mail_campaigns.schedule_modal.hint")}
          value={scheduleValue}
          onChange={(event) => setScheduleValue(event.currentTarget.value)}
          error={
            scheduleIsValid ? null : t("mail_campaigns.schedule_modal.past")
          }
        />
      </MailCampaignConfirmModal>

      <MailCampaignConfirmModal
        opened={action === "delete"}
        title={t("mail_campaigns.delete_modal.title")}
        confirmLabel={t("mail_campaigns.delete")}
        confirmColor="red"
        isPending={isWorking}
        onConfirm={() => void confirmDelete()}
        onClose={() => setAction(null)}
      >
        <Text>
          {t("mail_campaigns.delete_modal.message", {
            name: campaign?.name ?? "",
          })}
        </Text>
      </MailCampaignConfirmModal>
    </Paper>
  );
};
export default MailCampaignEditor;
