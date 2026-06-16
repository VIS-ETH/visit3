import {
  Badge,
  Box,
  Button,
  Divider,
  FileInput,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconBook2,
  IconCheck,
  IconDownload,
  IconPlayerPlay,
  IconTrash,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  KpEventBookletExportTaskStatus,
  type BookletAssetsResponse,
  type BookletExportTaskResponse,
} from "../orval/generated/fastAPI.schemas";
import {
  getBookletExportTaskDownloadUrl,
  getGetBookletAssetsQueryKey,
  getListBookletExportTasksQueryKey,
  useCreateBookletExportTask,
  useDeleteBookletAsset,
  useGetBookletAssets,
  useListBookletExportTasks,
  useUploadBookletAsset,
} from "../orval/generated/kp/kp";

const ASSET_TYPES = ["intro_page", "blank_page", "missing_advertisement"] as const;
type AssetType = (typeof ASSET_TYPES)[number];

const ACTIVE_STATUSES: KpEventBookletExportTaskStatus[] = [
  KpEventBookletExportTaskStatus.PENDING,
  KpEventBookletExportTaskStatus.RUNNING,
];

const BookletTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: assets, isLoading: isLoadingAssets } =
    useGetBookletAssets(eventId);
  const { data: tasks, isLoading: isLoadingTasks } = useListBookletExportTasks(
    eventId,
    {
      query: {
        refetchInterval: (query) => {
          const next = query.state.data;
          if (!next || !Array.isArray(next)) return false;
          return next.some((task) => ACTIVE_STATUSES.includes(task.status))
            ? 2000
            : false;
        },
      },
    },
  );

  const invalidateTasks = () =>
    queryClient.invalidateQueries({
      queryKey: getListBookletExportTasksQueryKey(eventId),
    });

  const { mutate: createTask, isPending: isCreatingTask } =
    useCreateBookletExportTask({
      mutation: {
        onSuccess: async () => {
          await invalidateTasks();
          notifications.show({
            color: "green",
            message: t("kp.manage.booklet.export_queued"),
          });
        },
        onError: () => {
          notifications.show({
            color: "red",
            message: t("kp.manage.booklet.export_queue_error"),
          });
        },
      },
    });

  const hasActiveTask = (tasks ?? []).some((task) =>
    ACTIVE_STATUSES.includes(task.status),
  );

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="lg">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={3}>{t("kp.manage.booklet.title")}</Title>
            <Text c="dimmed" size="sm">
              {t("kp.manage.booklet.description")}
            </Text>
          </div>
        </Group>

        <Divider />

        <Stack gap="sm">
          <Title order={4}>{t("kp.manage.booklet.assets_title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.manage.booklet.assets_description")}
          </Text>
          {isLoadingAssets ? (
            <Loader size="sm" />
          ) : (
            <Stack gap="sm">
              {ASSET_TYPES.map((assetType) => (
                <BookletAssetRow
                  key={assetType}
                  eventId={eventId}
                  assetType={assetType}
                  assets={assets ?? null}
                />
              ))}
            </Stack>
          )}
        </Stack>

        <Divider />

        <Stack gap="sm">
          <Group justify="space-between" align="center">
            <div>
              <Title order={4}>{t("kp.manage.booklet.export_title")}</Title>
              <Text c="dimmed" size="sm">
                {t("kp.manage.booklet.export_description")}
              </Text>
            </div>
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              loading={isCreatingTask}
              disabled={hasActiveTask}
              onClick={() => createTask({ eventId })}
            >
              {hasActiveTask
                ? t("kp.manage.booklet.export_running")
                : t("kp.manage.booklet.export_run")}
            </Button>
          </Group>

          {isLoadingTasks ? (
            <Loader size="sm" />
          ) : (tasks ?? []).length === 0 ? (
            <Text c="dimmed" size="sm">
              {t("kp.manage.booklet.export_history_empty")}
            </Text>
          ) : (
            <Stack gap="xs">
              {(tasks ?? []).map((task) => (
                <BookletTaskRow key={task.id} task={task} />
              ))}
            </Stack>
          )}
        </Stack>
      </Stack>
    </Paper>
  );
};

const BookletAssetRow = ({
  eventId,
  assetType,
  assets,
}: {
  eventId: string;
  assetType: AssetType;
  assets: BookletAssetsResponse | null;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const stored = assets?.[assetType] ?? null;

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getGetBookletAssetsQueryKey(eventId),
    });

  const { mutate: upload, isPending: isUploading } = useUploadBookletAsset({
    mutation: {
      onSuccess: async () => {
        setPendingFile(null);
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.booklet.asset_uploaded"),
        });
      },
      onError: () => {
        notifications.show({
          color: "red",
          message: t("kp.manage.booklet.asset_upload_error"),
        });
      },
    },
  });
  const { mutate: remove, isPending: isDeleting } = useDeleteBookletAsset({
    mutation: {
      onSuccess: async () => {
        await invalidate();
        notifications.show({
          color: "green",
          message: t("kp.manage.booklet.asset_deleted"),
        });
      },
      onError: () => {
        notifications.show({
          color: "red",
          message: t("kp.manage.booklet.asset_delete_error"),
        });
      },
    },
  });

  const labelKey = `kp.manage.booklet.asset_${assetType}`;
  const descriptionKey = `kp.manage.booklet.asset_${assetType}_description`;

  const handleUpload = () => {
    if (!pendingFile) return;
    upload({
      eventId,
      assetType,
      data: { file: pendingFile },
    });
  };

  const handleDelete = () => {
    if (!confirm(t("kp.manage.booklet.asset_delete_confirm"))) return;
    remove({ eventId, assetType });
  };

  return (
    <Box
      p="sm"
      style={{
        border: "1px solid var(--visit-border)",
        borderRadius: 8,
      }}
    >
      <Stack gap="xs">
        <Group justify="space-between" align="center">
          <div>
            <Text fw={500} size="sm">
              {t(labelKey)}
            </Text>
            <Text c="dimmed" size="xs">
              {t(descriptionKey)}
            </Text>
          </div>
          <Badge
            color={stored ? "green" : "gray"}
            variant="light"
            leftSection={stored ? <IconCheck size={12} /> : null}
          >
            {stored
              ? stored.original_filename
              : t("kp.manage.booklet.asset_missing")}
          </Badge>
        </Group>

        <Group align="end" gap="xs" wrap="wrap">
          <FileInput
            accept="application/pdf"
            placeholder={
              stored
                ? t("kp.manage.booklet.asset_replace")
                : t("kp.manage.booklet.asset_upload")
            }
            leftSection={<IconUpload size={14} />}
            value={pendingFile}
            onChange={setPendingFile}
            size="xs"
            style={{ flex: "1 1 320px" }}
          />
          <Button
            size="xs"
            onClick={handleUpload}
            loading={isUploading}
            disabled={!pendingFile}
          >
            {stored
              ? t("kp.manage.booklet.asset_replace")
              : t("kp.manage.booklet.asset_upload")}
          </Button>
          {stored ? (
            <Button
              size="xs"
              variant="subtle"
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={handleDelete}
              loading={isDeleting}
            >
              {t("kp.manage.booklet.asset_delete")}
            </Button>
          ) : null}
        </Group>
      </Stack>
    </Box>
  );
};

const BookletTaskRow = ({ task }: { task: BookletExportTaskResponse }) => {
  const { t } = useTranslation();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const response = await getBookletExportTaskDownloadUrl(task.id);
      window.open(response.url, "_blank", "noopener,noreferrer");
    } catch {
      notifications.show({
        color: "red",
        message: t("kp.manage.booklet.download_error"),
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const statusColor = (() => {
    switch (task.status) {
      case KpEventBookletExportTaskStatus.COMPLETED:
        return "green";
      case KpEventBookletExportTaskStatus.FAILED:
        return "red";
      case KpEventBookletExportTaskStatus.RUNNING:
        return "blue";
      default:
        return "gray";
    }
  })();

  const statusKey = `kp.manage.booklet.status_${task.status.toLowerCase()}`;
  const createdAt = new Date(task.created_at).toLocaleString();

  return (
    <Box
      p="sm"
      style={{
        border: "1px solid var(--visit-border)",
        borderRadius: 8,
      }}
    >
      <Group justify="space-between" align="center">
        <Group gap="sm" align="center">
          <IconBook2 size={20} />
          <Stack gap={0}>
            <Group gap="xs" align="center">
              <Badge color={statusColor} variant="light">
                {t(statusKey)}
              </Badge>
              <Text size="sm">{createdAt}</Text>
            </Group>
            {task.error ? (
              <Group gap={4}>
                <IconX size={12} color="red" />
                <Text size="xs" c="red">
                  {task.error}
                </Text>
              </Group>
            ) : null}
          </Stack>
        </Group>

        {task.status === KpEventBookletExportTaskStatus.COMPLETED &&
        task.output_file ? (
          <Button
            size="xs"
            leftSection={<IconDownload size={14} />}
            loading={isDownloading}
            onClick={handleDownload}
          >
            {t("kp.manage.booklet.task_download")}
          </Button>
        ) : null}
      </Group>
    </Box>
  );
};

export default BookletTab;
