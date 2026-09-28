import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconCopy } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router";
import BackButton from "../components/BackButton";
import { useGetKpById } from "../orval/generated/kp/kp";
import CloneKpModal from "../components/kp/CloneKpModal";
import { formatKpDisplayDate } from "../utils/kp-utils";
import BookingsTab from "../components/BookingsTab";
import BoothZonesTab from "../components/BoothZonesTab";
import DetailsTab from "../components/DetailsTab";
import IndustriesTab from "../components/IndustriesTab";
import ServicesTab from "../components/ServicesTab";
import ExportsTab from "../components/ExportsTab";
import VenueTab from "../components/kp/VenueTab";
import { useCurrentUser } from "../context/useCurrentUser";
function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

const KP_MANAGE_TAB_VALUES = [
  "details",
  "exports",
  "services",
  "booth_zones",
  "venue",
  "bookings",
  "industries",
] as const;

type KpManageTabValue = (typeof KP_MANAGE_TAB_VALUES)[number];

const DEFAULT_KP_MANAGE_TAB: KpManageTabValue = "details";

const PRESIDENT_KP_MANAGE_TAB_VALUES: readonly KpManageTabValue[] = [
  "services",
  "booth_zones",
  "venue",
  "industries",
];

function isKpManageTabValue(v: string | null): v is KpManageTabValue {
  return v !== null && KP_MANAGE_TAB_VALUES.includes(v as KpManageTabValue);
}

function isVisibleTab(v: KpManageTabValue, isPresident: boolean): boolean {
  return isPresident || !PRESIDENT_KP_MANAGE_TAB_VALUES.includes(v);
}

const KpManage = () => {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { user } = useCurrentUser();
  const [searchParams, setSearchParams] = useSearchParams();
  const [cloneModalOpen, setCloneModalOpen] = useState(false);
  const { data: event, isLoading, isError } = useGetKpById(id ?? "");

  const isPresident = user?.is_kp_president ?? false;
  const tabParam = searchParams.get("tab");
  const activeTab: KpManageTabValue =
    isKpManageTabValue(tabParam) && isVisibleTab(tabParam, isPresident)
      ? tabParam
      : DEFAULT_KP_MANAGE_TAB;

  useEffect(() => {
    if (tabParam === null) return;
    if (isKpManageTabValue(tabParam) && isVisibleTab(tabParam, isPresident)) {
      return;
    }
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete("tab");
        return next;
      },
      { replace: true },
    );
  }, [tabParam, isPresident, setSearchParams]);

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
          <Tabs.Tab value="bookings">{t("kp.manage.tab_bookings")}</Tabs.Tab>
          {isPresident && (
            <>
              <Tabs.Tab value="services">
                {t("kp.manage.tab_services")}
              </Tabs.Tab>
              <Tabs.Tab value="booth_zones">
                {t("kp.manage.tab_booth_zones")}
              </Tabs.Tab>
              <Tabs.Tab value="venue">{t("kp.venue.tab_title")}</Tabs.Tab>
              <Tabs.Tab value="industries">
                {t("kp.manage.tab_industries")}
              </Tabs.Tab>
            </>
          )}
        </Tabs.List>

        <Tabs.Panel value="details" pt="md">
          <DetailsTab eventId={id} />
        </Tabs.Panel>
        <Tabs.Panel value="exports" pt="md">
          <ExportsTab
            eventId={id}
            eventName={event.name}
            canManageBooklet={user?.is_admin ?? false}
          />
        </Tabs.Panel>
        <Tabs.Panel value="bookings" pt="md">
          <BookingsTab eventId={id} />
        </Tabs.Panel>
        {isPresident && (
          <>
            <Tabs.Panel value="services" pt="md">
              <ServicesTab eventId={id} />
            </Tabs.Panel>
            <Tabs.Panel value="booth_zones" pt="md">
              <BoothZonesTab eventId={id} />
            </Tabs.Panel>
            <Tabs.Panel value="venue" pt="md">
              <VenueTab eventId={id} />
            </Tabs.Panel>
            <Tabs.Panel value="industries" pt="md">
              <IndustriesTab />
            </Tabs.Panel>
          </>
        )}
      </Tabs>
    </Stack>
  );
};
export default KpManage;
