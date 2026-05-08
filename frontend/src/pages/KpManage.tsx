import {
  Alert,
  Center,
  Group,
  Loader,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router";
import BackButton from "../components/BackButton";
import { useGetKpById } from "../orval/generated/kp/kp";
import { formatKpDisplayDate } from "../utils/kp-utils";
import BookingsTab from "../components/BookingsTab";
import BoothZonesTab from "../components/BoothZonesTab";
import DetailsTab from "../components/DetailsTab";
import IndustriesTab from "../components/IndustriesTab";
import ServicesTab from "../components/ServicesTab";
import ExportsTab from "../components/ExportsTab";

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
] as const;

type KpManageTabValue = (typeof KP_MANAGE_TAB_VALUES)[number];

const DEFAULT_KP_MANAGE_TAB: KpManageTabValue = "details";

function isKpManageTabValue(v: string | null): v is KpManageTabValue {
  return v !== null && KP_MANAGE_TAB_VALUES.includes(v as KpManageTabValue);
}

// ─── Main Page ───

const KpManage = () => {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
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
      </Group>

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
      </Tabs>
    </Stack>
  );
};
export default KpManage;
