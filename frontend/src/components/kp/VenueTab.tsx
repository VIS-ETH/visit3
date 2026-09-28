import {
  ActionIcon,
  Button,
  Center,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getGetEventVenueQueryKey,
  getListVenueLayoutsQueryKey,
  useCreateVenueLayout,
  useDeleteVenueLayout,
  useListBoothZones,
  useListVenueLayouts,
  useUpdateVenueLayout,
} from "../../orval/generated/kp/kp";
import ManageEntityModal from "../ManageEntityModal";
import type { KpVenueFloorPlan } from "../../orval/generated/fastAPI.schemas";
import VenueLayoutEditor from "../venue/VenueLayoutEditor";
import { FLOOR_PLANS } from "../venue/floor-plans";

const DEFAULT_LAYOUT_WIDTH = 1000;
const DEFAULT_LAYOUT_HEIGHT = 700;

interface LayoutFormValues {
  name: string;
  width: number;
  height: number;
  order: number;
  floorPlan: KpVenueFloorPlan | null;
}

const emptyLayoutForm: LayoutFormValues = {
  name: "",
  width: DEFAULT_LAYOUT_WIDTH,
  height: DEFAULT_LAYOUT_HEIGHT,
  order: 0,
  floorPlan: null,
};

const toNumber = (value: string | number) =>
  typeof value === "number" ? value : Number(value) || 0;

const VenueTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: layouts, isLoading } = useListVenueLayouts(eventId);
  const { data: zones } = useListBoothZones(eventId);
  const [selectedLayoutId, setSelectedLayoutId] = useState<string | null>(null);
  const [editingLayoutId, setEditingLayoutId] = useState<string | null>(null);
  const [form, setForm] = useState<LayoutFormValues>(emptyLayoutForm);
  const [isEditorDirty, setIsEditorDirty] = useState(false);
  const [opened, { open, close }] = useDisclosure(false);

  const sortedLayouts = [...(layouts ?? [])].sort((a, b) => a.order - b.order);
  const selectedLayout =
    sortedLayouts.find((layout) => layout.id === selectedLayoutId) ??
    sortedLayouts.at(0);

  useEffect(() => {
    if (selectedLayout === undefined) return;
    if (selectedLayout.id === selectedLayoutId) return;
    setSelectedLayoutId(selectedLayout.id);
  }, [selectedLayout, selectedLayoutId]);

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: getListVenueLayoutsQueryKey(eventId),
      }),
      queryClient.invalidateQueries({
        queryKey: getGetEventVenueQueryKey(eventId),
      }),
    ]);

  const notifySuccess = (message: string) =>
    notifications.show({ color: "green", message });

  const mayDiscardChanges = () =>
    !isEditorDirty || confirm(t("kp.venue.unsaved_changes_confirm"));

  const closeModal = () => {
    close();
    setEditingLayoutId(null);
    setForm(emptyLayoutForm);
  };

  const { mutate: createLayout, isPending: isCreating } = useCreateVenueLayout({
    mutation: {
      onSuccess: async (layout) => {
        await invalidate();
        setSelectedLayoutId(layout.id);
        closeModal();
        notifySuccess(t("kp.venue.layout_created"));
      },
    },
  });

  const { mutate: updateLayout, isPending: isUpdating } = useUpdateVenueLayout({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        if (editingLayoutId !== null) closeModal();
        notifySuccess(t("kp.venue.layout_updated"));
      },
    },
  });

  const { mutate: removeLayout } = useDeleteVenueLayout({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        setSelectedLayoutId(null);
        notifySuccess(t("kp.venue.layout_deleted"));
      },
    },
  });

  const openCreateModal = () => {
    setEditingLayoutId(null);
    setForm({ ...emptyLayoutForm, order: sortedLayouts.length });
    open();
  };

  const openEditModal = (layout: (typeof sortedLayouts)[number]) => {
    setEditingLayoutId(layout.id);
    setForm({
      name: layout.name,
      width: layout.width,
      height: layout.height,
      order: layout.order,
      floorPlan: layout.floor_plan,
    });
    open();
  };

  const submitModal = () => {
    const data = {
      name: form.name.trim(),
      order: form.order,
      floor_plan: form.floorPlan,
      ...(form.floorPlan === null
        ? { width: form.width, height: form.height }
        : {}),
    };
    if (editingLayoutId !== null) {
      updateLayout({ layoutId: editingLayoutId, data });
      return;
    }
    createLayout({ eventId, data });
  };

  return (
    <>
      <ManageEntityModal
        isSaving={isCreating || isUpdating}
        isSubmitDisabled={form.name.trim() === ""}
        onClose={closeModal}
        onSubmit={submitModal}
        opened={opened}
        submitLabel={
          editingLayoutId !== null
            ? t("kp.venue.layout_edit")
            : t("kp.venue.layout_add")
        }
        title={
          editingLayoutId !== null
            ? t("kp.venue.layout_edit")
            : t("kp.venue.layout_add")
        }
      >
        <TextInput
          label={t("kp.venue.layout_name")}
          onChange={(event) =>
            setForm({ ...form, name: event.currentTarget.value })
          }
          value={form.name}
        />
        <Select
          allowDeselect={false}
          data={[
            { value: "", label: t("kp.venue.floor_plan_none") },
            ...FLOOR_PLANS.map((floorPlan) => ({
              value: floorPlan,
              label: t(`kp.venue.floor_plan_${floorPlan}`),
            })),
          ]}
          label={t("kp.venue.floor_plan")}
          onChange={(value) =>
            setForm({
              ...form,
              floorPlan: FLOOR_PLANS.find((plan) => plan === value) ?? null,
            })
          }
          value={form.floorPlan ?? ""}
        />
        {form.floorPlan === null ? (
          <Group grow>
            <NumberInput
              label={t("kp.venue.layout_width")}
              min={1}
              onChange={(value) => setForm({ ...form, width: toNumber(value) })}
              value={form.width}
            />
            <NumberInput
              label={t("kp.venue.layout_height")}
              min={1}
              onChange={(value) =>
                setForm({ ...form, height: toNumber(value) })
              }
              value={form.height}
            />
          </Group>
        ) : null}
        <NumberInput
          label={t("kp.venue.layout_order")}
          min={0}
          onChange={(value) => setForm({ ...form, order: toNumber(value) })}
          value={form.order}
        />
      </ManageEntityModal>

      <Stack gap="md">
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <Group justify="space-between">
              <Title order={4}>{t("kp.venue.layouts_title")}</Title>
              <Button
                leftSection={<IconPlus size={16} />}
                onClick={openCreateModal}
                size="xs"
              >
                {t("kp.venue.layout_add")}
              </Button>
            </Group>

            {isLoading ? (
              <Center py="xl">
                <Loader />
              </Center>
            ) : sortedLayouts.length === 0 ? (
              <Text c="dimmed" size="sm">
                {t("kp.venue.layouts_empty")}
              </Text>
            ) : (
              <Stack gap="xs">
                {sortedLayouts.map((layout) => (
                  <Paper
                    key={layout.id}
                    p="sm"
                    radius="md"
                    style={{
                      borderColor:
                        layout.id === selectedLayout?.id
                          ? "var(--mantine-color-brand-5)"
                          : undefined,
                      borderWidth: layout.id === selectedLayout?.id ? 2 : 1,
                    }}
                    withBorder
                  >
                    <Group justify="space-between" wrap="nowrap">
                      <UnstyledButton
                        onClick={() => {
                          if (!mayDiscardChanges()) return;
                          setSelectedLayoutId(layout.id);
                        }}
                        style={{ flex: 1, textAlign: "left" }}
                      >
                        <Text fw={600} size="sm">
                          {layout.name}
                        </Text>
                        <Text c="dimmed" size="xs">
                          {t("kp.venue.layout_size", {
                            width: layout.width,
                            height: layout.height,
                          })}
                        </Text>
                      </UnstyledButton>
                      <Switch
                        checked={layout.is_active}
                        label={t("kp.venue.layout_active")}
                        onChange={(event) =>
                          updateLayout({
                            layoutId: layout.id,
                            data: { is_active: event.currentTarget.checked },
                          })
                        }
                      />
                      <ActionIcon
                        aria-label={t("kp.venue.layout_edit")}
                        onClick={() => openEditModal(layout)}
                        variant="subtle"
                      >
                        <IconEdit size={16} />
                      </ActionIcon>
                      <ActionIcon
                        aria-label={t("kp.venue.layout_delete")}
                        color="red"
                        onClick={() => {
                          if (!confirm(t("kp.venue.layout_confirm_delete"))) {
                            return;
                          }
                          removeLayout({ layoutId: layout.id });
                        }}
                        variant="subtle"
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Group>
                  </Paper>
                ))}
              </Stack>
            )}
          </Stack>
        </Paper>

        {selectedLayout ? (
          <VenueLayoutEditor
            key={selectedLayout.id}
            layout={selectedLayout}
            onDirtyChange={setIsEditorDirty}
            zones={zones ?? []}
          />
        ) : null}
      </Stack>
    </>
  );
};

export default VenueTab;
