import {
  Badge,
  Box,
  Button,
  Card,
  Divider,
  FileInput,
  Group,
  Input,
  Select,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconDownload, IconPhotoUp } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
  useGetNametagExportBackground,
  useListNametagExportTargets,
  useUploadNametagExportBackground,
} from "../../orval/generated/kp/kp";
import { downloadBlob, safeFilenamePart } from "../../utils/download";

const downloadRequestOptions = { responseType: "blob" as const };
type EventDownloadFunction = (eventId: string) => unknown;
type NametagExportScope = "event" | "company" | "person";

export default function ExportsTab({
  eventId,
  eventName,
}: {
  eventId: string;
  eventName: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
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
  const eventSlug = safeFilenamePart(eventName);

  const { data: nametagBackground, isLoading: isBackgroundLoading } =
    useGetNametagExportBackground(eventId);
  const { data: nametagExportTargets } = useListNametagExportTargets(eventId);

  useEffect(() => {
    setSelectedNameTagId(null);
  }, [selectedNametagBookingId]);

  const { mutate: uploadBackground, isPending: isUploadingBackground } =
    useUploadNametagExportBackground({
      mutation: {
        onSuccess: async () => {
          setBackgroundFile(null);
          await queryClient.invalidateQueries({
            queryKey: getGetNametagExportBackgroundQueryKey(eventId),
          });
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
    if (!backgroundFile) return;
    uploadBackground({
      eventId,
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
      filename: `${eventSlug}-bookings-all.csv`,
      download: (targetEventId: string) =>
        downloadEventBookingsCsv(targetEventId, downloadRequestOptions),
    },
    {
      key: "bookings_by_zone",
      label: t("kp.dashboard.exports.downloads.bookings_by_zone"),
      filename: `${eventSlug}-bookings-by-zone.zip`,
      download: (targetEventId: string) =>
        downloadEventBookingsByZoneZip(targetEventId, downloadRequestOptions),
    },
    {
      key: "waitlist",
      label: t("kp.dashboard.exports.downloads.waitlist"),
      filename: `${eventSlug}-waitlist-companies.csv`,
      download: (targetEventId: string) =>
        downloadEventWaitlistCompaniesCsv(
          targetEventId,
          downloadRequestOptions,
        ),
    },
    {
      key: "booked_services",
      label: t("kp.dashboard.exports.downloads.booked_services"),
      filename: `${eventSlug}-booked-services.csv`,
      download: (targetEventId: string) =>
        downloadEventBookedServicesCsv(targetEventId, downloadRequestOptions),
    },
    {
      key: "nametags_data",
      label: t("kp.dashboard.exports.downloads.nametags_data"),
      filename: `${eventSlug}-nametags-data.csv`,
      download: (targetEventId: string) =>
        downloadEventNametagsDataCsv(targetEventId, downloadRequestOptions),
    },
    {
      key: "company_details",
      label: t("kp.dashboard.exports.downloads.company_details"),
      filename: `${eventSlug}-company-details.csv`,
      download: (targetEventId: string) =>
        downloadEventCompanyDetailsCsv(targetEventId, downloadRequestOptions),
    },
    {
      key: "service_requirements",
      label: t("kp.dashboard.exports.downloads.service_requirements"),
      filename: `${eventSlug}-service-requirements-status.csv`,
      download: (targetEventId: string) =>
        downloadEventServiceRequirementsCsv(
          targetEventId,
          downloadRequestOptions,
        ),
    },
    {
      key: "booth_zone_capacity",
      label: t("kp.dashboard.exports.downloads.booth_zone_capacity"),
      filename: `${eventSlug}-booth-zone-capacity.csv`,
      download: (targetEventId: string) =>
        downloadEventBoothZoneCapacityCsv(
          targetEventId,
          downloadRequestOptions,
        ),
    },
    {
      key: "contacts",
      label: t("kp.dashboard.exports.downloads.contacts"),
      filename: `${eventSlug}-contacts.csv`,
      download: (targetEventId: string) =>
        downloadEventContactsCsv(targetEventId, downloadRequestOptions),
    },
    {
      key: "registration_exceptions",
      label: t("kp.dashboard.exports.downloads.registration_exceptions"),
      filename: `${eventSlug}-registration-exceptions.csv`,
      download: (targetEventId: string) =>
        downloadEventRegistrationExceptionsCsv(
          targetEventId,
          downloadRequestOptions,
        ),
    },
  ];

  const handleDownload = async (
    key: string,
    filename: string,
    download: EventDownloadFunction,
  ) => {
    setActiveDownload(key);
    try {
      const content = await download(eventId);
      downloadBlob(content, filename);
    } finally {
      setActiveDownload(null);
    }
  };

  const handleNametagDownload = async () => {
    const key = "nametags_pdf";
    setActiveDownload(key);
    try {
      const content = await downloadEventNametags(
        eventId,
        undefined,
        downloadRequestOptions,
      );
      downloadBlob(content, `${eventSlug}-nametags.pdf`);
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
        `${eventSlug}-${safeFilenamePart(
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
        `${eventSlug}-${safeFilenamePart(
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
    (nametagExportScope === "company" && !selectedNametagBookingId) ||
    (nametagExportScope === "person" && !selectedNameTagId);

  return (
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
            {eventName}
          </Badge>
        </Group>

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
              leftSection={nametagBackground ? <IconCheck size={14} /> : null}
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
              placeholder={t("kp.dashboard.exports.background_placeholder")}
              accept="image/png,image/jpeg"
              value={backgroundFile}
              onChange={setBackgroundFile}
              flex={1}
            />
            <Button
              onClick={handleBackgroundUpload}
              loading={isUploadingBackground}
              disabled={!backgroundFile}
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
              <Input.Wrapper
                label={t("kp.dashboard.exports.scope_label")}
                w={{ base: "100%", sm: 420 }}
              >
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
                  w="100%"
                />
              </Input.Wrapper>

              {nametagExportScope === "company" ? (
                <Select
                  label={t("kp.dashboard.exports.company")}
                  placeholder={t("kp.dashboard.exports.company_placeholder")}
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
                    placeholder={t("kp.dashboard.exports.company_placeholder")}
                    data={nametagCompanyOptions}
                    value={selectedNametagBookingId}
                    onChange={setSelectedNametagBookingId}
                    searchable
                    flex={1}
                  />
                  <Select
                    label={t("kp.dashboard.exports.person")}
                    placeholder={t("kp.dashboard.exports.person_placeholder")}
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
          <Title order={5}>{t("kp.dashboard.exports.data_title")}</Title>
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
                leftSection={<IconDownload size={16} />}
                justify="flex-start"
              >
                {exportDownload.label}
              </Button>
            ))}
          </SimpleGrid>
        </Stack>
      </Stack>
    </Card>
  );
}
