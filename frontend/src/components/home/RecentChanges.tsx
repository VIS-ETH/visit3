import {
  Anchor,
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconCalendarEvent, IconChecks } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import {
  getGetRecentChangesQueryKey,
  useGetRecentChanges,
  useMarkChangesSeen,
} from "../../orval/generated/changes/changes";
import type { ChangedBookingResult } from "../../orval/generated/fastAPI.schemas";
import { KpBookingStatusBadge } from "../KpBookingStatusBadge";

const PREVIEW_COUNT = 5;

const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const bookingChangesPath = (eventId: string) =>
  `/kp/${eventId}?tab=bookings&changes=1`;

type ChangeItem = { key: string; label: ReactNode; detail: ReactNode };

const ChangeColumn = ({
  title,
  total,
  items,
  allPath,
}: {
  title: string;
  total: number;
  items: ChangeItem[];
  allPath: string | null;
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
            <Stack gap={0} key={item.key}>
              <Text size="sm" truncate="end">
                {item.label}
              </Text>
              <Text c="dimmed" size="xs" component="div">
                {item.detail}
              </Text>
            </Stack>
          ))
        )}
        {total > 0 && allPath ? (
          <Anchor component={NavLink} size="sm" to={allPath}>
            {t("changes.show_all", { total })}
          </Anchor>
        ) : null}
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
  detail: (
    <Group gap={6} wrap="nowrap">
      <KpBookingStatusBadge status={booking.status} size="xs" />
      <span>
        {booking.event_name} · {booking.booth_zone_name} ·{" "}
        {dateTimeFormat.format(new Date(at))}
      </span>
    </Group>
  ),
});

const RecentChanges = ({ latestEventId }: { latestEventId: string | null }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: changes, isLoading } = useGetRecentChanges();
  const { mutate: markSeen, isPending: isMarking } = useMarkChangesSeen({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetRecentChangesQueryKey(),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Paper withBorder p="lg" radius="md">
        <Loader size="sm" />
      </Paper>
    );
  }
  if (!changes) return null;

  const bookingEventId =
    changes.new_bookings.at(0)?.event_id ??
    changes.changed_bookings.at(0)?.event_id ??
    latestEventId;
  const bookingsPath = bookingEventId
    ? bookingChangesPath(bookingEventId)
    : null;

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Stack gap={2}>
            <Title order={3}>{t("changes.title")}</Title>
            <Text c="dimmed" size="sm">
              {t("changes.since", {
                since: dateTimeFormat.format(new Date(changes.since)),
              })}
            </Text>
          </Stack>
          <Group gap="sm">
            {bookingsPath ? (
              <Button
                component={NavLink}
                leftSection={<IconCalendarEvent size={16} />}
                to={bookingsPath}
                variant="light"
              >
                {t("changes.open_bookings")}
              </Button>
            ) : null}
            <Button
              leftSection={<IconChecks size={16} />}
              loading={isMarking}
              onClick={() => markSeen()}
              variant="default"
            >
              {t("changes.mark_seen")}
            </Button>
          </Group>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          <ChangeColumn
            title={t("changes.new_bookings")}
            total={changes.new_bookings_total}
            items={changes.new_bookings.map((booking) =>
              bookingItem(booking, booking.created_at),
            )}
            allPath={bookingsPath}
          />
          <ChangeColumn
            title={t("changes.changed_bookings")}
            total={changes.changed_bookings_total}
            items={changes.changed_bookings.map((booking) =>
              bookingItem(booking, booking.changed_at),
            )}
            allPath={bookingsPath}
          />
          <ChangeColumn
            title={t("changes.new_companies")}
            total={changes.new_companies_total}
            items={changes.new_companies.map((company) => ({
              key: company.id,
              label: company.name,
              detail: (
                <Group gap={6} wrap="nowrap">
                  {company.confirmed_at === null ? (
                    <Badge color="yellow" size="xs" variant="light">
                      {t("company_management.unconfirmed")}
                    </Badge>
                  ) : null}
                  <span>
                    {dateTimeFormat.format(new Date(company.created_at))}
                  </span>
                </Group>
              ),
            }))}
            allPath="/company-management?changes=1"
          />
          <ChangeColumn
            title={t("changes.new_users")}
            total={changes.new_users_total}
            items={changes.new_users.map((user) => ({
              key: user.id,
              label:
                [user.first_name, user.last_name].filter(Boolean).join(" ") ||
                user.email,
              detail: [
                user.company_name,
                dateTimeFormat.format(new Date(user.created_at)),
              ]
                .filter(Boolean)
                .join(" · "),
            }))}
            allPath="/user-management?filter=new"
          />
        </SimpleGrid>
      </Stack>
    </Paper>
  );
};

export default RecentChanges;
