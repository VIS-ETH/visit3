import {
  Anchor,
  Badge,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconChecks } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import {
  getGetRecentChangesQueryKey,
  useGetRecentChanges,
  useMarkChangesSeen,
} from "../../orval/generated/changes/changes";
import type {
  ChangedBookingResult,
  ChangedEventResult,
} from "../../orval/generated/fastAPI.schemas";
import { KpBookingStatusBadge } from "../KpBookingStatusBadge";
import { formatDateTime } from "../../utils/date-format";
import { useAsyncAction } from "../../hooks/use-async-action";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";

const PREVIEW_COUNT = 5;

const bookingChangesPath = (eventId: string) =>
  `/kp/${eventId}?tab=bookings&changes=1`;

type ChangeItem = {
  key: string;
  label: string;
  badge?: ReactNode;
  info: string;
};
type ChangeLink = { path: string; label: string };

const ChangeColumn = ({
  title,
  total,
  items,
  links,
}: {
  title: string;
  total: number;
  items: ChangeItem[];
  links: ChangeLink[];
}) => {
  const { t } = useTranslation();

  return (
    <Paper withBorder p="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" wrap="nowrap">
          <Text fw={600}>{title}</Text>
          <Badge color={total > 0 ? "orange" : "gray"} variant="light">
            {total}
          </Badge>
        </Group>
        {items.length === 0 ? (
          <Text c="dimmed" size="sm">
            {t("changes.none")}
          </Text>
        ) : (
          items.slice(0, PREVIEW_COUNT).map((item) => (
            <Tooltip key={item.key} label={item.info} openDelay={200}>
              <Group gap={6} wrap="nowrap">
                <Text size="sm" truncate="end">
                  {item.label}
                </Text>
                {item.badge}
              </Group>
            </Tooltip>
          ))
        )}
        {total > 0
          ? links.map((link) => (
              <Anchor
                component={NavLink}
                key={link.path}
                size="sm"
                to={link.path}
              >
                {link.label}
              </Anchor>
            ))
          : null}
      </Stack>
    </Paper>
  );
};

const bookingItem = (
  booking: ChangedBookingResult,
  at: string,
): ChangeItem => ({
  key: booking.id,
  label: booking.company_name,
  badge: <KpBookingStatusBadge status={booking.status} size="xs" />,
  info: [booking.event_name, booking.booth_zone_name, formatDateTime(at)].join(
    " · ",
  ),
});

const RecentChanges = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: changes, isPending, isError } = useGetRecentChanges();
  const { mutateAsync: markChangesSeen } = useMarkChangesSeen();
  const { run: markSeen, isRunning: isMarking } = useAsyncAction(
    async (asOf: string) => {
      await markChangesSeen({ data: { as_of: asOf } });
      await queryClient.invalidateQueries({
        queryKey: getGetRecentChangesQueryKey(),
      });
    },
  );

  if (isPending) {
    return (
      <Paper withBorder p="lg" radius="md">
        <PageLoader />
      </Paper>
    );
  }
  if (isError) return <ErrorAlert />;

  const bookingLinks = (
    events: ChangedEventResult[],
    total: number,
  ): ChangeLink[] =>
    events.map((event) => ({
      path: bookingChangesPath(event.id),
      label:
        events.length > 1
          ? t("changes.show_event", { event: event.name })
          : t("changes.show_all", { total }),
    }));

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Stack gap={2}>
            <Title order={3}>{t("changes.title")}</Title>
            <Text c="dimmed" size="sm">
              {t("changes.since", {
                since: formatDateTime(changes.since),
              })}
            </Text>
          </Stack>
          <Button
            leftSection={<IconChecks size={16} />}
            loading={isMarking}
            onClick={() => void markSeen(changes.as_of)}
            variant="default"
          >
            {t("changes.mark_seen")}
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          <ChangeColumn
            title={t("changes.new_bookings")}
            total={changes.new_bookings_total}
            items={changes.new_bookings.map((booking) =>
              bookingItem(booking, booking.created_at),
            )}
            links={bookingLinks(
              changes.new_booking_events,
              changes.new_bookings_total,
            )}
          />
          <ChangeColumn
            title={t("changes.changed_bookings")}
            total={changes.changed_bookings_total}
            items={changes.changed_bookings.map((booking) =>
              bookingItem(booking, booking.changed_at),
            )}
            links={bookingLinks(
              changes.changed_booking_events,
              changes.changed_bookings_total,
            )}
          />
          <ChangeColumn
            title={t("changes.new_companies")}
            total={changes.new_companies_total}
            items={changes.new_companies.map((company) => ({
              key: company.id,
              label: company.name,
              badge:
                company.confirmed_at === null ? (
                  <Badge color="yellow" size="xs" variant="light">
                    {t("company_management.unconfirmed")}
                  </Badge>
                ) : null,
              info: formatDateTime(company.created_at) ?? "",
            }))}
            links={[
              {
                path: "/company-management?filter=new",
                label: t("changes.show_all", {
                  total: changes.new_companies_total,
                }),
              },
            ]}
          />
          <ChangeColumn
            title={t("changes.new_users")}
            total={changes.new_users_total}
            items={changes.new_users.map((user) => ({
              key: user.id,
              label:
                [user.first_name, user.last_name].filter(Boolean).join(" ") ||
                user.email,
              info: [user.company_name, formatDateTime(user.created_at)]
                .filter(Boolean)
                .join(" · "),
            }))}
            links={[
              {
                path: "/user-management?filter=new",
                label: t("changes.show_all", {
                  total: changes.new_users_total,
                }),
              },
            ]}
          />
        </SimpleGrid>
      </Stack>
    </Paper>
  );
};

export default RecentChanges;
