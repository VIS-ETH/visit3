import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Center,
  ColorInput,
  Group,
  Loader,
  Modal,
  NumberInput,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../components/BackButton";
import {
  formatKpDateInput,
  formatKpDisplayDate,
  kpSchema,
  toKpIsoDate,
  type KpFormValues,
} from "../schemas/kpSchema";
import { useTranslatedForm } from "../utils/translator";
import {
  getGetKpByIdQueryKey,
  getListBoothZonesQueryKey,
  getListIndustriesQueryKey,
  getListKpsQueryKey,
  getListServicesQueryKey,
  useCreateBoothZone,
  useCreateIndustry,
  useCreateService,
  useDeleteBoothZone,
  useDeleteIndustry,
  useDeleteService,
  useGetKpById,
  useListBoothZones,
  useListEventBookings,
  useListIndustries,
  useListServices,
  useUpdateKp,
  useUpdateService,
} from "../orval/generated/kp/kp";

function formatDate(dateString?: string) {
  return formatKpDisplayDate(dateString);
}

const dateFieldNames = [
  "registrationOpen",
  "registrationEnd",
  "finalizationDeadline",
  "nametagsDeadline",
  "eventDate",
] as const;

// ─── Details Tab ───

function DetailsTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: event } = useGetKpById(eventId);

  const form = useTranslatedForm<typeof kpSchema>(kpSchema, {
    initialValues: {
      name: event?.name ?? "",
      registrationOpen: event?.registration_open
        ? formatKpDateInput(new Date(event.registration_open))
        : "",
      registrationEnd: event?.registration_end
        ? formatKpDateInput(new Date(event.registration_end))
        : "",
      finalizationDeadline: event?.finalization_deadline
        ? formatKpDateInput(new Date(event.finalization_deadline))
        : "",
      nametagsDeadline: event?.nametags_deadline
        ? formatKpDateInput(new Date(event.nametags_deadline))
        : "",
      eventDate: event?.event_date
        ? formatKpDateInput(new Date(event.event_date))
        : "",
    },
    validateInputOnChange: true,
  });

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

  const { mutate: update, isPending } = useUpdateKp({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetKpByIdQueryKey(eventId),
        });
        await queryClient.invalidateQueries({ queryKey: getListKpsQueryKey() });
        notifications.show({
          color: "green",
          message: t("kp.manage.edit_success"),
        });
      },
    },
  });

  const handleSubmit = (values: KpFormValues) => {
    update({
      eventId,
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

  return (
    <Card withBorder radius="md" p="md">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <Title order={4}>{t("kp.manage.edit_title")}</Title>
          <Group grow>
            <TextInput
              label={t("kp.dashboard.name")}
              disabled={isPending}
              {...form.getInputProps("name")}
            />
            <TextInput
              label={t("kp.dashboard.registration_open")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              description={t("kp.dashboard.date_input_hint")}
              disabled={isPending}
              {...getDateInputProps("registrationOpen")}
            />
          </Group>
          <Group grow>
            <TextInput
              label={t("kp.dashboard.registration_end")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              description={t("kp.dashboard.date_input_hint")}
              disabled={isPending}
              {...getDateInputProps("registrationEnd")}
            />
            <TextInput
              label={t("kp.dashboard.finalization_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              description={t("kp.dashboard.date_input_hint")}
              disabled={isPending}
              {...getDateInputProps("finalizationDeadline")}
            />
          </Group>
          <Group grow>
            <TextInput
              label={t("kp.dashboard.nametags_deadline")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              description={t("kp.dashboard.date_input_hint")}
              disabled={isPending}
              {...getDateInputProps("nametagsDeadline")}
            />
            <TextInput
              label={t("kp.dashboard.event_date")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              description={t("kp.dashboard.date_input_hint")}
              disabled={isPending}
              {...getDateInputProps("eventDate")}
            />
          </Group>
          <Group justify="flex-end">
            <Button
              type="submit"
              loading={isPending}
              disabled={isPending || !form.isValid()}
            >
              {t("kp.manage.save")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}

// ─── Services Tab ───

function ServicesTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: services, isLoading } = useListServices(eventId);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState<number>(0);
  const [maxPerBooking, setMaxPerBooking] = useState<number>(1);
  const [maxTotal, setMaxTotal] = useState<number>(0);
  const [isActive, setIsActive] = useState(true);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListServicesQueryKey(eventId),
    });

  const { mutate: create, isPending: isCreating } = useCreateService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        close();
        setName("");
        setDescription("");
        setPrice(0);
        setMaxPerBooking(1);
        setMaxTotal(0);
        setIsActive(true);
        notifications.show({
          color: "green",
          message: t("kp.manage.service_created"),
        });
      },
    },
  });

  const { mutate: update } = useUpdateService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_updated"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteService({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.service_deleted"),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.services_title")}</Title>
        <Button leftSection={<IconPlus size={16} />} size="xs" onClick={open}>
          {t("kp.manage.services_add")}
        </Button>
      </Group>

      <Modal
        opened={opened}
        onClose={close}
        title={t("kp.manage.services_add")}
        centered
      >
        <Stack gap="sm">
          <TextInput
            label={t("kp.manage.service_name")}
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            disabled={isCreating}
          />
          <Textarea
            label={t("kp.manage.service_description")}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            disabled={isCreating}
          />
          <Group grow>
            <NumberInput
              label={t("kp.manage.service_price")}
              value={price}
              onChange={(v) => setPrice(Number(v) || 0)}
              min={0}
              disabled={isCreating}
            />
            <NumberInput
              label={t("kp.manage.service_max_per_booking")}
              value={maxPerBooking}
              onChange={(v) => setMaxPerBooking(Number(v) || 1)}
              min={1}
              disabled={isCreating}
            />
          </Group>
          <Group grow>
            <NumberInput
              label={t("kp.manage.service_max_total")}
              value={maxTotal}
              onChange={(v) => setMaxTotal(Number(v) || 0)}
              min={0}
              disabled={isCreating}
            />
            <Switch
              label={t("kp.manage.service_active")}
              checked={isActive}
              onChange={(e) => setIsActive(e.currentTarget.checked)}
              disabled={isCreating}
              mt="xl"
            />
          </Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={close} disabled={isCreating}>
              {t("common.cancel")}
            </Button>
            <Button
              loading={isCreating}
              disabled={!name.trim()}
              onClick={() =>
                create({
                  eventId,
                  data: {
                    name: name.trim(),
                    description,
                    price,
                    max_quantity_per_booking: maxPerBooking,
                    max_total_quantity: maxTotal,
                    is_active: isActive,
                  },
                })
              }
            >
              {t("kp.manage.services_add")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {services && services.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.service_name")}</Table.Th>
              <Table.Th>{t("kp.manage.service_price")}</Table.Th>
              <Table.Th>{t("kp.manage.service_max_per_booking")}</Table.Th>
              <Table.Th>{t("kp.manage.service_active")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {services.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td fw={500}>{s.name}</Table.Td>
                <Table.Td>{(s.price / 100).toFixed(2)}</Table.Td>
                <Table.Td>{s.max_quantity_per_booking}</Table.Td>
                <Table.Td>
                  <Switch
                    checked={s.is_active}
                    onChange={(e) =>
                      update({
                        serviceId: s.id,
                        data: { is_active: e.currentTarget.checked },
                      })
                    }
                    size="sm"
                  />
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.service_confirm_delete"))) {
                        remove({ serviceId: s.id });
                      }
                    }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.services_empty")}</Text>
      )}
    </Stack>
  );
}

// ─── Booth Zones Tab ───

function BoothZonesTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: zones, isLoading } = useListBoothZones(eventId);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState("#000000");
  const [capacity, setCapacity] = useState<number>(0);
  const [boothSize, setBoothSize] = useState<number>(0);
  const [basePrice, setBasePrice] = useState<number>(0);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListBoothZonesQueryKey(eventId),
    });

  const { mutate: create, isPending: isCreating } = useCreateBoothZone({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        close();
        setName("");
        setDescription("");
        setColor("#000000");
        setCapacity(0);
        setBoothSize(0);
        setBasePrice(0);
        notifications.show({
          color: "green",
          message: t("kp.manage.zone_created"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteBoothZone({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.zone_deleted"),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.booth_zones_title")}</Title>
        <Button leftSection={<IconPlus size={16} />} size="xs" onClick={open}>
          {t("kp.manage.booth_zones_add")}
        </Button>
      </Group>

      <Modal
        opened={opened}
        onClose={close}
        title={t("kp.manage.booth_zones_add")}
        centered
      >
        <Stack gap="sm">
          <TextInput
            label={t("kp.manage.zone_name")}
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            disabled={isCreating}
          />
          <Textarea
            label={t("kp.manage.zone_description")}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            disabled={isCreating}
          />
          <ColorInput
            label={t("kp.manage.zone_color")}
            value={color}
            onChange={setColor}
            disabled={isCreating}
          />
          <Group grow>
            <NumberInput
              label={t("kp.manage.zone_capacity")}
              value={capacity}
              onChange={(v) => setCapacity(Number(v) || 0)}
              min={0}
              disabled={isCreating}
            />
            <NumberInput
              label={t("kp.manage.zone_booth_size")}
              value={boothSize}
              onChange={(v) => setBoothSize(Number(v) || 0)}
              min={0}
              decimalScale={2}
              disabled={isCreating}
            />
          </Group>
          <NumberInput
            label={t("kp.manage.zone_base_price")}
            value={basePrice}
            onChange={(v) => setBasePrice(Number(v) || 0)}
            min={0}
            disabled={isCreating}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={close} disabled={isCreating}>
              {t("common.cancel")}
            </Button>
            <Button
              loading={isCreating}
              disabled={!name.trim()}
              onClick={() =>
                create({
                  eventId,
                  data: {
                    name: name.trim(),
                    description,
                    color,
                    capacity,
                    booth_size: boothSize,
                    base_price: basePrice,
                  },
                })
              }
            >
              {t("kp.manage.booth_zones_add")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {zones && zones.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th />
              <Table.Th>{t("kp.manage.zone_name")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_capacity")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_booth_size")}</Table.Th>
              <Table.Th>{t("kp.manage.zone_base_price")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {zones.map((z) => (
              <Table.Tr key={z.id}>
                <Table.Td>
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: 4,
                      backgroundColor: z.color,
                    }}
                  />
                </Table.Td>
                <Table.Td fw={500}>{z.name}</Table.Td>
                <Table.Td>{z.capacity}</Table.Td>
                <Table.Td>{z.booth_size} m²</Table.Td>
                <Table.Td>{(z.base_price / 100).toFixed(2)}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.zone_confirm_delete"))) {
                        remove({ boothZoneId: z.id });
                      }
                    }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.booth_zones_empty")}</Text>
      )}
    </Stack>
  );
}

// ─── Industries Tab ───

function IndustriesTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: industries, isLoading } = useListIndustries();
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getListIndustriesQueryKey(),
    });

  const { mutate: create, isPending: isCreating } = useCreateIndustry({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        close();
        setName("");
        notifications.show({
          color: "green",
          message: t("kp.manage.industry_created"),
        });
      },
    },
  });

  const { mutate: remove } = useDeleteIndustry({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.industry_deleted"),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>{t("kp.manage.industries_title")}</Title>
        <Button leftSection={<IconPlus size={16} />} size="xs" onClick={open}>
          {t("kp.manage.industries_add")}
        </Button>
      </Group>

      <Modal
        opened={opened}
        onClose={close}
        title={t("kp.manage.industries_add")}
        centered
      >
        <Stack gap="sm">
          <TextInput
            label={t("kp.manage.industry_name")}
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            disabled={isCreating}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={close} disabled={isCreating}>
              {t("common.cancel")}
            </Button>
            <Button
              loading={isCreating}
              disabled={!name.trim()}
              onClick={() => create({ data: { name: name.trim() } })}
            >
              {t("kp.manage.industries_add")}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {industries && industries.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.industry_name")}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {industries.map((ind) => (
              <Table.Tr key={ind.id}>
                <Table.Td fw={500}>{ind.name}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      if (confirm(t("kp.manage.industry_confirm_delete"))) {
                        remove({ industryId: ind.id });
                      }
                    }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.industries_empty")}</Text>
      )}
    </Stack>
  );
}

// ─── Bookings Tab ───

function BookingsTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const { data: bookings, isLoading } = useListEventBookings(eventId);

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  const statusColors: Record<string, string> = {
    draft: "gray",
    registered: "blue",
    finalized: "yellow",
    confirmed: "green",
    cancelled: "red",
  };

  return (
    <Stack gap="md">
      <Title order={4}>{t("kp.manage.bookings_title")}</Title>
      {bookings && bookings.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.booking_company")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_booth_zone")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_booth_nr")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_status")}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bookings.map((b) => (
              <Table.Tr key={b.id}>
                <Table.Td>{b.company_id}</Table.Td>
                <Table.Td>{b.booth_zone_id}</Table.Td>
                <Table.Td>{b.booth_nr}</Table.Td>
                <Table.Td>
                  <Badge
                    color={statusColors[b.status] ?? "gray"}
                    variant="light"
                    size="sm"
                  >
                    {b.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.bookings_empty")}</Text>
      )}
    </Stack>
  );
}

// ─── Main Page ───

export default function KpManage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data: event, isLoading, isError } = useGetKpById(id ?? "");

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

      <Tabs defaultValue="details">
        <Tabs.List>
          <Tabs.Tab value="details">{t("kp.manage.tab_details")}</Tabs.Tab>
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
}
