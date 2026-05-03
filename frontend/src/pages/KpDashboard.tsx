import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Divider,
  FileInput,
  Group,
  Loader,
  Modal,
  Select,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconDownload,
  IconPhotoUp,
  IconPlus,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ChangeEvent } from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import BackButton from "../components/BackButton";
import {
  formatKpDateInput,
  formatKpDisplayDate,
  kpSchema,
  toKpIsoDate,
  type KpFormValues,
} from "../schemas/kpSchema";
import { downloadBlob, safeFilenamePart } from "../utils/download";
import { useTranslatedForm } from "../utils/translator";
import {
  downloadBookingNametags,
  downloadEventBookedServicesCsv,
  downloadEventBookingsByZoneZip,
  downloadEventBookingsCsv,
  downloadEventBoothZoneCapacityCsv,
  downloadEventCompanyDetailsCsv,
  downloadEventContactsCsv,
  downloadEventNametags,
  downloadEventNametagsDataCsv,
  downloadEventRegistrationExceptionsCsv,
  downloadEventServiceRequirementsCsv,
  downloadEventWaitlistCompaniesCsv,
  downloadSingleNametag,
  getGetNametagExportBackgroundQueryKey,
  getGetLatestKpQueryKey,
  getListKpsQueryKey,
  useCreateKp,
  useGetNametagExportBackground,
  useListNametagExportTargets,
  useListKps,
  useUploadNametagExportBackground,
} from "../orval/generated/kp/kp";
import type { KpResponse } from "../orval/generated/fastAPI.schemas";

type EventStatus = "upcoming" | "registration_open" | "finalizing" | "past";

function getEventStatus(event: KpResponse): EventStatus {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const regOpen = event.registration_open
    ? new Date(event.registration_open)
    : null;
  const regEnd = event.registration_end
    ? new Date(event.registration_end)
    : null;
  const eventDate = event.event_date ? new Date(event.event_date) : null;

  if (eventDate && today > eventDate) return "past";
  if (regOpen && today < regOpen) return "upcoming";
  if (regEnd && today <= regEnd) return "registration_open";
  return "finalizing";
}

const STATUS_COLORS: Record<EventStatus, string> = {
  upcoming: "blue",
  registration_open: "green",
  finalizing: "yellow",
  past: "gray",
};

function todayAsDateInput() {
  return formatKpDateInput(new Date());
}

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

const downloadRequestOptions = { responseType: "blob" as const };
type EventDownloadFunction = (eventId: string) => unknown;
type NametagExportScope = "event" | "company" | "person";

function eventSelectOptions(events: KpResponse[] | undefined) {
  return (events ?? [])
    .filter((event): event is KpResponse & { id: string } => Boolean(event.id))
    .map((event) => ({
      value: event.id,
      label: `${event.name} (${formatKpDisplayDate(event.event_date)})`,
    }));
}

export default function KpDashboard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [nametagExportScope, setNametagExportScope] =
    useState<NametagExportScope>("event");
  const [selectedNametagBookingId, setSelectedNametagBookingId] = useState<
    string | null
  >(null);
  const [selectedNameTagId, setSelectedNameTagId] = useState<string | null>(
    null,
  );
  const [backgroundFile, setBackgroundFile] = useState<File | null>(null);
  const [activeDownload, setActiveDownload] = useState<string | null>(null);

  const initialValues: KpFormValues = {
    name: "",
    registrationOpen: todayAsDateInput(),
    registrationEnd: todayAsDateInput(),
    finalizationDeadline: todayAsDateInput(),
    nametagsDeadline: todayAsDateInput(),
    eventDate: todayAsDateInput(),
  };
  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues,
    validateInputOnChange: true,
  });

  const getDateInputProps = (field: (typeof dateFieldNames)[number]) => {
    const inputProps = form.getInputProps(field);

    return {
      ...inputProps,
      onChange: (event: ChangeEvent<HTMLInputElement>) => {
        inputProps.onChange(event);
        for (const fieldName of dateFieldNames) {
          form.validateField(fieldName);
        }
      },
    };
  };

  const { data: events, isLoading, isError } = useListKps();
  const selectedEvent = events?.find((event) => event.id === selectedEventId);
  const selectedEventSlug = safeFilenamePart(selectedEvent?.name ?? "kp");
  const selectedEventOptions = eventSelectOptions(events);
  const statusLabels: Record<EventStatus, string> = {
    upcoming: t("kp.dashboard.status_upcoming"),
    registration_open: t("kp.dashboard.status_registration_open"),
    finalizing: t("kp.dashboard.status_finalizing"),
    past: t("kp.dashboard.status_past"),
  };

  useEffect(() => {
    const firstEventId = events?.find((event) => event.id)?.id;
    if (!selectedEventId && firstEventId) {
      setSelectedEventId(firstEventId);
    }
  }, [events, selectedEventId]);

  const { data: nametagBackground, isLoading: isBackgroundLoading } =
    useGetNametagExportBackground(selectedEventId ?? "", {
      query: { enabled: Boolean(selectedEventId) },
    });
  const { data: nametagExportTargets } = useListNametagExportTargets(
    selectedEventId ?? "",
    {
      query: { enabled: Boolean(selectedEventId) },
    },
  );

  useEffect(() => {
    setSelectedNametagBookingId(null);
    setSelectedNameTagId(null);
  }, [selectedEventId]);

  useEffect(() => {
    setSelectedNameTagId(null);
  }, [selectedNametagBookingId]);

  const { mutate: createEvent, isPending: isCreating } = useCreateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        await queryClient.invalidateQueries({
          queryKey: getGetLatestKpQueryKey(),
        });
        form.reset();
        closeModal();

        notifications.show({
          color: "green",
          title: t("kp.dashboard.create_success_title"),
          message: t("kp.dashboard.create_success_message"),
        });
      },
    },
  });

  const handleCreate = (values: KpFormValues) => {
    createEvent({
      data: {
        name: values.name.trim(),
        registration_open: toKpIsoDate(values.registrationOpen),
        registration_end: toKpIsoDate(values.registrationEnd),
        finalization_deadline: toKpIsoDate(values.finalizationDeadline),
        nametags_deadline: toKpIsoDate(values.nametagsDeadline),
        event_date: toKpIsoDate(values.eventDate),
      },
    });
  };

  const { mutate: uploadBackground, isPending: isUploadingBackground } =
    useUploadNametagExportBackground({
      mutation: {
        onSuccess: async () => {
          setBackgroundFile(null);
          if (selectedEventId) {
            await queryClient.invalidateQueries({
              queryKey: getGetNametagExportBackgroundQueryKey(selectedEventId),
            });
          }
          notifications.show({
            color: "green",
            title: t("kp.dashboard.exports.background_upload_success_title"),
            message: t(
              "kp.dashboard.exports.background_upload_success_message",
            ),
          });
        },
      },
    });

  const handleBackgroundUpload = () => {
    if (!selectedEventId || !backgroundFile) return;
    uploadBackground({
      eventId: selectedEventId,
      data: { file: backgroundFile },
    });
  };

  const nametagCompanyOptions = (nametagExportTargets?.companies ?? []).map(
    (company) => ({
      value: company.booking_id,
      label: `${company.company_name} (${company.nametag_count})`,
    }),
  );
  const selectedNametagCompany = nametagExportTargets?.companies.find(
    (company) => company.booking_id === selectedNametagBookingId,
  );
  const selectedNametagPerson = nametagExportTargets?.people.find(
    (person) => person.id === selectedNameTagId,
  );
  const nametagPersonOptions = (nametagExportTargets?.people ?? [])
    .filter((person) => person.booking_id === selectedNametagBookingId)
    .map((person) => ({
      value: person.id,
      label: `${person.first_name} ${person.last_name}`,
    }));

  const exportDownloads = [
    {
      key: "bookings",
      label: t("kp.dashboard.exports.downloads.bookings"),
      filename: `${selectedEventSlug}-bookings-all.csv`,
      download: (eventId: string) =>
        downloadEventBookingsCsv(eventId, downloadRequestOptions),
    },
    {
      key: "bookings_by_zone",
      label: t("kp.dashboard.exports.downloads.bookings_by_zone"),
      filename: `${selectedEventSlug}-bookings-by-zone.zip`,
      download: (eventId: string) =>
        downloadEventBookingsByZoneZip(eventId, downloadRequestOptions),
    },
    {
      key: "waitlist",
      label: t("kp.dashboard.exports.downloads.waitlist"),
      filename: `${selectedEventSlug}-waitlist-companies.csv`,
      download: (eventId: string) =>
        downloadEventWaitlistCompaniesCsv(eventId, downloadRequestOptions),
    },
    {
      key: "booked_services",
      label: t("kp.dashboard.exports.downloads.booked_services"),
      filename: `${selectedEventSlug}-booked-services.csv`,
      download: (eventId: string) =>
        downloadEventBookedServicesCsv(eventId, downloadRequestOptions),
    },
    {
      key: "nametags_data",
      label: t("kp.dashboard.exports.downloads.nametags_data"),
      filename: `${selectedEventSlug}-nametags-data.csv`,
      download: (eventId: string) =>
        downloadEventNametagsDataCsv(eventId, downloadRequestOptions),
    },
    {
      key: "company_details",
      label: t("kp.dashboard.exports.downloads.company_details"),
      filename: `${selectedEventSlug}-company-details.csv`,
      download: (eventId: string) =>
        downloadEventCompanyDetailsCsv(eventId, downloadRequestOptions),
    },
    {
      key: "service_requirements",
      label: t("kp.dashboard.exports.downloads.service_requirements"),
      filename: `${selectedEventSlug}-service-requirements-status.csv`,
      download: (eventId: string) =>
        downloadEventServiceRequirementsCsv(eventId, downloadRequestOptions),
    },
    {
      key: "booth_zone_capacity",
      label: t("kp.dashboard.exports.downloads.booth_zone_capacity"),
      filename: `${selectedEventSlug}-booth-zone-capacity.csv`,
      download: (eventId: string) =>
        downloadEventBoothZoneCapacityCsv(eventId, downloadRequestOptions),
    },
    {
      key: "contacts",
      label: t("kp.dashboard.exports.downloads.contacts"),
      filename: `${selectedEventSlug}-contacts.csv`,
      download: (eventId: string) =>
        downloadEventContactsCsv(eventId, downloadRequestOptions),
    },
    {
      key: "registration_exceptions",
      label: t("kp.dashboard.exports.downloads.registration_exceptions"),
      filename: `${selectedEventSlug}-registration-exceptions.csv`,
      download: (eventId: string) =>
        downloadEventRegistrationExceptionsCsv(eventId, downloadRequestOptions),
    },
  ];

  const handleDownload = async (
    key: string,
    filename: string,
    download: EventDownloadFunction,
  ) => {
    if (!selectedEventId) return;
    setActiveDownload(key);
    try {
      const content = await download(selectedEventId);
      downloadBlob(content, filename);
    } finally {
      setActiveDownload(null);
    }
  };

  const handleNametagDownload = async () => {
    if (!selectedEventId) return;
    const key = "nametags_pdf";
    setActiveDownload(key);
    try {
      const content = await downloadEventNametags(
        selectedEventId,
        undefined,
        downloadRequestOptions,
      );
      downloadBlob(content, `${selectedEventSlug}-nametags.pdf`);
    } finally {
      setActiveDownload(null);
    }
  };

  const handleCompanyNametagDownload = async () => {
    if (!selectedNametagBookingId || !selectedNametagCompany) return;
    const key = "nametags_company";
    setActiveDownload(key);
    try {
      const content = await downloadBookingNametags(
        selectedNametagBookingId,
        undefined,
        downloadRequestOptions,
      );
      downloadBlob(
        content,
        `${selectedEventSlug}-${safeFilenamePart(
          selectedNametagCompany.company_name,
        )}-nametags.pdf`,
      );
    } finally {
      setActiveDownload(null);
    }
  };

  const handleSingleNametagDownload = async () => {
    if (!selectedNameTagId || !selectedNametagPerson) return;
    const key = "nametags_person";
    setActiveDownload(key);
    try {
      const content = await downloadSingleNametag(
        selectedNameTagId,
        downloadRequestOptions,
      );
      downloadBlob(
        content,
        `${selectedEventSlug}-${safeFilenamePart(
          selectedNametagPerson.company_name,
        )}-${safeFilenamePart(
          `${selectedNametagPerson.first_name}-${selectedNametagPerson.last_name}`,
        )}-nametag.pdf`,
      );
    } finally {
      setActiveDownload(null);
    }
  };

  const handleScopedNametagDownload = () => {
    if (nametagExportScope === "company") {
      void handleCompanyNametagDownload();
      return;
    }
    if (nametagExportScope === "person") {
      void handleSingleNametagDownload();
      return;
    }
    void handleNametagDownload();
  };

  const scopedNametagDownloadLabel =
    nametagExportScope === "company"
      ? t("kp.dashboard.exports.download_company_nametags")
      : nametagExportScope === "person"
        ? t("kp.dashboard.exports.download_person_nametag")
        : t("kp.dashboard.exports.download_event_nametags");
  const scopedNametagDownloadLoading =
    activeDownload ===
    (nametagExportScope === "company"
      ? "nametags_company"
      : nametagExportScope === "person"
        ? "nametags_person"
        : "nametags_pdf");
  const scopedNametagDownloadDisabled =
    !nametagBackground ||
    (nametagExportScope === "event" && !selectedEventId) ||
    (nametagExportScope === "company" && !selectedNametagBookingId) ||
    (nametagExportScope === "person" && !selectedNameTagId);

  return (
    <Stack gap="md">
      <BackButton to="/" />

      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>{t("kp.dashboard.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.dashboard.description")}
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={openModal}>
          {t("kp.dashboard.create_new_button")}
        </Button>
      </Group>

      <Modal
        opened={modalOpened}
        onClose={closeModal}
        title={t("kp.dashboard.create_title")}
        size="lg"
        centered
      >
        <form onSubmit={form.onSubmit(handleCreate)}>
          <Stack gap="sm">
            <Group grow>
              <TextInput
                label={t("kp.dashboard.name")}
                placeholder="Kontaktparty 2026"
                disabled={isCreating}
                {...form.getInputProps("name")}
              />
              <TextInput
                label={t("kp.dashboard.registration_open")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("registrationOpen")}
              />
            </Group>
            <Group grow>
              <TextInput
                label={t("kp.dashboard.registration_end")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("registrationEnd")}
              />
              <TextInput
                label={t("kp.dashboard.finalization_deadline")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("finalizationDeadline")}
              />
            </Group>
            <Group grow>
              <TextInput
                label={t("kp.dashboard.nametags_deadline")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("nametagsDeadline")}
              />
              <TextInput
                label={t("kp.dashboard.event_date")}
                placeholder={t("kp.dashboard.date_input_placeholder")}
                description={t("kp.dashboard.date_input_hint")}
                disabled={isCreating}
                {...getDateInputProps("eventDate")}
              />
            </Group>
            <Group justify="flex-end">
              <Button
                variant="default"
                onClick={closeModal}
                disabled={isCreating}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="submit"
                loading={isCreating}
                disabled={isCreating || !form.isValid()}
              >
                {t("kp.dashboard.create_button")}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : null}

      {isError ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.dashboard.error")}
        </Alert>
      ) : null}

      {!isLoading && !isError ? (
        <Tabs defaultValue="events" keepMounted={false}>
          <Tabs.List>
            <Tabs.Tab value="events">{t("kp.dashboard.tabs.events")}</Tabs.Tab>
            <Tabs.Tab value="exports">
              {t("kp.dashboard.tabs.exports")}
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="events" pt="md">
            <Card withBorder radius="md" p={0}>
              {events && events.length > 0 ? (
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>{t("kp.dashboard.name")}</Table.Th>
                      <Table.Th>
                        {t("kp.dashboard.registration_window")}
                      </Table.Th>
                      <Table.Th>{t("kp.dashboard.event_date")}</Table.Th>
                      <Table.Th>
                        {t("kp.dashboard.finalization_deadline")}
                      </Table.Th>
                      <Table.Th>{t("kp.dashboard.nametags_deadline")}</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {events.map((event) => {
                      const status = getEventStatus(event);
                      return (
                        <Table.Tr
                          key={event.id ?? `${event.name}-${event.event_date}`}
                        >
                          <Table.Td fw={500}>{event.name}</Table.Td>
                          <Table.Td>
                            {formatKpDisplayDate(event.registration_open)} -{" "}
                            {formatKpDisplayDate(event.registration_end)}
                          </Table.Td>
                          <Table.Td>
                            {formatKpDisplayDate(event.event_date)}
                          </Table.Td>
                          <Table.Td>
                            {formatKpDisplayDate(event.finalization_deadline)}
                          </Table.Td>
                          <Table.Td>
                            {formatKpDisplayDate(event.nametags_deadline)}
                          </Table.Td>
                          <Table.Td>
                            <Badge
                              color={STATUS_COLORS[status]}
                              variant="light"
                              size="sm"
                            >
                              {statusLabels[status]}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Button
                              size="xs"
                              variant="light"
                              component={Link}
                              to={`/kp/${event.id}`}
                            >
                              {t("kp.dashboard.manage_button")}
                            </Button>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              ) : (
                <Text c="dimmed" p="md">
                  {t("kp.dashboard.no_events")}
                </Text>
              )}
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="exports" pt="md">
            <Card withBorder radius="md" p="lg">
              <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Title order={3}>{t("kp.dashboard.exports.title")}</Title>
                    <Text c="dimmed" size="sm">
                      {t("kp.dashboard.exports.description")}
                    </Text>
                  </div>
                  <Badge color="gray" variant="light" size="lg">
                    {selectedEvent?.name ?? t("kp.dashboard.exports.no_event")}
                  </Badge>
                </Group>

                {selectedEventOptions.length > 0 ? (
                  <>
                    <Select
                      label={t("kp.dashboard.exports.event")}
                      data={selectedEventOptions}
                      value={selectedEventId}
                      onChange={setSelectedEventId}
                      searchable
                    />

                    <Divider my="xs" />

                    <Stack gap="sm">
                      <Group justify="space-between" align="center">
                        <div>
                          <Title order={4}>
                            {t("kp.dashboard.exports.nametags_title")}
                          </Title>
                          <Text c="dimmed" size="sm">
                            {t("kp.dashboard.exports.nametags_description")}
                          </Text>
                        </div>
                        <Badge
                          color={nametagBackground ? "green" : "yellow"}
                          variant="light"
                          leftSection={
                            nametagBackground ? <IconCheck size={14} /> : null
                          }
                        >
                          {isBackgroundLoading
                            ? t("kp.dashboard.exports.background_loading")
                            : nametagBackground
                              ? t("kp.dashboard.exports.background_configured")
                              : t("kp.dashboard.exports.background_missing")}
                        </Badge>
                      </Group>

                      <Group align="end" gap="sm">
                        <FileInput
                          label={t("kp.dashboard.exports.background")}
                          placeholder={t(
                            "kp.dashboard.exports.background_placeholder",
                          )}
                          accept="image/png,image/jpeg"
                          value={backgroundFile}
                          onChange={setBackgroundFile}
                          flex={1}
                        />
                        <Button
                          onClick={handleBackgroundUpload}
                          loading={isUploadingBackground}
                          disabled={!selectedEventId || !backgroundFile}
                          variant="default"
                          leftSection={<IconPhotoUp size={16} />}
                        >
                          {t("kp.dashboard.exports.upload_background")}
                        </Button>
                      </Group>

                      <Box
                        p="sm"
                        style={{
                          border: "1px solid var(--visit-border)",
                          borderRadius: 8,
                        }}
                      >
                        <Group align="end" gap="sm">
                          <SegmentedControl
                            value={nametagExportScope}
                            onChange={(value) =>
                              setNametagExportScope(value as NametagExportScope)
                            }
                            data={[
                              {
                                value: "event",
                                label: t("kp.dashboard.exports.scope_event"),
                              },
                              {
                                value: "company",
                                label: t("kp.dashboard.exports.scope_company"),
                              },
                              {
                                value: "person",
                                label: t("kp.dashboard.exports.scope_person"),
                              },
                            ]}
                            w={{ base: "100%", sm: 420 }}
                          />

                          {nametagExportScope === "company" ? (
                            <Select
                              label={t("kp.dashboard.exports.company")}
                              placeholder={t(
                                "kp.dashboard.exports.company_placeholder",
                              )}
                              data={nametagCompanyOptions}
                              value={selectedNametagBookingId}
                              onChange={setSelectedNametagBookingId}
                              searchable
                              flex={1}
                            />
                          ) : null}

                          {nametagExportScope === "person" ? (
                            <>
                              <Select
                                label={t("kp.dashboard.exports.company")}
                                placeholder={t(
                                  "kp.dashboard.exports.company_placeholder",
                                )}
                                data={nametagCompanyOptions}
                                value={selectedNametagBookingId}
                                onChange={setSelectedNametagBookingId}
                                searchable
                                flex={1}
                              />
                              <Select
                                label={t("kp.dashboard.exports.person")}
                                placeholder={t(
                                  "kp.dashboard.exports.person_placeholder",
                                )}
                                data={nametagPersonOptions}
                                value={selectedNameTagId}
                                onChange={setSelectedNameTagId}
                                searchable
                                disabled={!selectedNametagBookingId}
                                flex={1}
                              />
                            </>
                          ) : null}

                          <Button
                            onClick={handleScopedNametagDownload}
                            loading={scopedNametagDownloadLoading}
                            disabled={scopedNametagDownloadDisabled}
                            leftSection={<IconDownload size={16} />}
                            ml="auto"
                          >
                            {scopedNametagDownloadLabel}
                          </Button>
                        </Group>
                      </Box>
                    </Stack>

                    <Divider my="xs" />

                    <Stack gap="sm">
                      <Title order={5}>
                        {t("kp.dashboard.exports.data_title")}
                      </Title>
                      <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }} spacing="xs">
                        {exportDownloads.map((exportDownload) => (
                          <Button
                            key={exportDownload.key}
                            variant="default"
                            onClick={() =>
                              handleDownload(
                                exportDownload.key,
                                exportDownload.filename,
                                exportDownload.download,
                              )
                            }
                            loading={activeDownload === exportDownload.key}
                            disabled={!selectedEventId}
                            leftSection={<IconDownload size={16} />}
                            justify="flex-start"
                          >
                            {exportDownload.label}
                          </Button>
                        ))}
                      </SimpleGrid>
                    </Stack>
                  </>
                ) : (
                  <Text c="dimmed">{t("kp.dashboard.exports.no_events")}</Text>
                )}
              </Stack>
            </Card>
          </Tabs.Panel>
        </Tabs>
      ) : null}
    </Stack>
  );
}
