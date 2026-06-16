import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconCopy } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router";
import BackButton from "../components/BackButton";
import {
  getListKpsQueryKey,
  useCloneKp,
  useGetKpById,
} from "../orval/generated/kp/kp";
import { kpSchema, toKpRequest, type KpFormValues } from "../schemas/kpSchema";
import { formatKpDisplayDate } from "../utils/kp-utils";
import BookingsTab from "../components/BookingsTab";
import BoothZonesTab from "../components/BoothZonesTab";
import DetailsTab from "../components/DetailsTab";
import IndustriesTab from "../components/IndustriesTab";
import ServicesTab from "../components/ServicesTab";
import BookletTab from "../components/BookletTab";
import ExportsTab from "../components/ExportsTab";
import { useTranslatedForm } from "../utils/translator";

function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

const KP_MANAGE_TAB_VALUES = [
  "details",
  "exports",
  "services",
  "booth_zones",
  "bookings",
  "industries",
  "booklet",
] as const;

type KpManageTabValue = (typeof KP_MANAGE_TAB_VALUES)[number];

const DEFAULT_KP_MANAGE_TAB: KpManageTabValue = "details";

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

function isKpManageTabValue(v: string | null): v is KpManageTabValue {
  return v !== null && KP_MANAGE_TAB_VALUES.includes(v as KpManageTabValue);
}

const emptyKpFormValues: KpFormValues = {
  name: "",
  registrationOpen: "",
  registrationEnd: "",
  finalizationDeadline: "",
  nametagsDeadline: "",
  eventDate: "",
};

const CloneKpModal = ({
  eventId,
  opened,
  onClose,
}: {
  eventId: string;
  opened: boolean;
  onClose: () => void;
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues: emptyKpFormValues,
    validateInputOnChange: true,
  });

  const { mutate: clone, isPending } = useCloneKp({
    mutation: {
      onSuccess: async (clonedEvent) => {
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        notifications.show({
          color: "green",
          message: t("kp.manage.clone_success"),
        });
        form.setValues(emptyKpFormValues);
        onClose();
        navigate(`/kp/${clonedEvent.id}`);
      },
    },
  });

  const closeAndReset = () => {
    form.setValues(emptyKpFormValues);
    onClose();
  };

  const getDateInputProps = (field: (typeof dateFieldNames)[number]) => {
    const inputProps = form.getInputProps(field);
    return {
      ...inputProps,
      onChange: (e: ChangeEvent<HTMLInputElement>) => {
        inputProps.onChange(e);
        for (const f of dateFieldNames) form.validateField(f);
      },
    };
  };

  const handleSubmit = (values: KpFormValues) => {
    clone({
      eventId,
      data: toKpRequest(values),
    });
  };

  return (
    <Modal
      opened={opened}
      onClose={closeAndReset}
      title={t("kp.manage.clone_title")}
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label={t("kp.dashboard.name")}
              disabled={isPending}
              {...form.getInputProps("name")}
            />
            <TextInput
              label={t("kp.dashboard.registration_open")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("registrationOpen")}
            />
            <TextInput
              label={t("kp.dashboard.registration_end")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("registrationEnd")}
            />
            <TextInput
              label={t("kp.dashboard.finalization_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("finalizationDeadline")}
            />
            <TextInput
              label={t("kp.dashboard.nametags_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("nametagsDeadline")}
            />
            <TextInput
              label={t("kp.dashboard.event_date")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              disabled={isPending}
              {...getDateInputProps("eventDate")}
            />
          </SimpleGrid>
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={closeAndReset}
              disabled={isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              loading={isPending}
              disabled={!form.isValid()}
            >
              {t("kp.manage.clone_submit")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

// ─── Main Page ───

const KpManage = () => {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [cloneModalOpen, setCloneModalOpen] = useState(false);
  const { data: event, isLoading, isError } = useGetKpById(id ?? "");

  const tabParam = searchParams.get("tab");
  const activeTab: KpManageTabValue = isKpManageTabValue(tabParam)
    ? tabParam
    : DEFAULT_KP_MANAGE_TAB;

  useEffect(() => {
    if (tabParam !== null && !isKpManageTabValue(tabParam)) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete("tab");
          return next;
        },
        { replace: true },
      );
    }
  }, [tabParam, setSearchParams]);

  const setActiveTabInUrl = (value: string | null) => {
    const next = new URLSearchParams(searchParams);
    const v = value as KpManageTabValue | null;
    if (v && v !== DEFAULT_KP_MANAGE_TAB) {
      next.set("tab", v);
    } else {
      next.delete("tab");
    }
    setSearchParams(next, { replace: true });
  };

  if (!id) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.not_found")}
        </Alert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Center py="xl">
          <Loader />
        </Center>
      </Stack>
    );
  }

  if (isError || !event) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <Alert icon={<IconAlertCircle />} color="red">
          {t("kp.manage.not_found")}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <BackButton to="/kp" />

      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>
            {event.name} — {t("kp.manage.title")}
          </Title>
          <Text c="dimmed" size="sm">
            {formatDate(event.event_date)}
          </Text>
        </div>
        <Button
          leftSection={<IconCopy size={16} />}
          onClick={() => setCloneModalOpen(true)}
        >
          {t("kp.manage.clone")}
        </Button>
      </Group>

      <CloneKpModal
        eventId={id}
        opened={cloneModalOpen}
        onClose={() => setCloneModalOpen(false)}
      />

      <Tabs value={activeTab} onChange={setActiveTabInUrl}>
        <Tabs.List>
          <Tabs.Tab value="details">{t("kp.manage.tab_details")}</Tabs.Tab>
          <Tabs.Tab value="exports">{t("kp.manage.tab_exports")}</Tabs.Tab>
          <Tabs.Tab value="services">{t("kp.manage.tab_services")}</Tabs.Tab>
          <Tabs.Tab value="booth_zones">
            {t("kp.manage.tab_booth_zones")}
          </Tabs.Tab>
          <Tabs.Tab value="bookings">{t("kp.manage.tab_bookings")}</Tabs.Tab>
          <Tabs.Tab value="industries">
            {t("kp.manage.tab_industries")}
          </Tabs.Tab>
          <Tabs.Tab value="booklet">{t("kp.manage.tab_booklet")}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="details" pt="md">
          <DetailsTab eventId={id} />
        </Tabs.Panel>
        <Tabs.Panel value="exports" pt="md">
          <ExportsTab eventId={id} eventName={event.name} />
        </Tabs.Panel>
        <Tabs.Panel value="services" pt="md">
          <ServicesTab eventId={id} />
        </Tabs.Panel>
        <Tabs.Panel value="booth_zones" pt="md">
          <BoothZonesTab eventId={id} />
        </Tabs.Panel>
        <Tabs.Panel value="bookings" pt="md">
          <BookingsTab eventId={id} />
        </Tabs.Panel>
        <Tabs.Panel value="industries" pt="md">
          <IndustriesTab />
        </Tabs.Panel>
        <Tabs.Panel value="booklet" pt="md">
          <BookletTab eventId={id} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};
export default KpManage;
