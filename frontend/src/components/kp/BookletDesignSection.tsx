import {
  Button,
  Group,
  Image,
  Paper,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconDownload, IconFileUpload, IconRestore } from "@tabler/icons-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getGetBookletBackgroundQueryKey,
  previewBookletSample,
  useGetBookletBackground,
  useResetBookletBackground,
  useUploadBookletBackground,
} from "../../orval/generated/kp/kp";
import { PDF_UPLOAD_ACCEPT } from "../../utils/upload-formats";
import { useWarnOnLeave } from "../../utils/use-warn-on-leave";
import RepickableFileButton from "../RepickableFileButton";

const MAX_BACKGROUND_SIZE_BYTES = 900 * 1024;
const PREVIEW_WIDTH = 320;

const BookletDesignSection = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [fileError, setFileError] = useState<string | null>(null);
  const { data: background, isLoading } = useGetBookletBackground(eventId);

  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: getGetBookletBackgroundQueryKey(eventId),
    });

  const { mutate: upload, isPending: isUploading } = useUploadBookletBackground(
    { mutation: { onSuccess: refresh } },
  );
  const { mutate: reset, isPending: isResetting } = useResetBookletBackground({
    mutation: { onSuccess: refresh },
  });
  useWarnOnLeave(isUploading);

  const { data: preview } = useQuery({
    queryKey: [
      "booklet-sample",
      eventId,
      background?.filename ?? null,
      background?.size_bytes ?? null,
    ],
    queryFn: () => previewBookletSample(eventId),
    enabled: !isLoading,
  });

  const handleFile = (file: File | null) => {
    setFileError(null);
    if (!file) return;
    if (file.size > MAX_BACKGROUND_SIZE_BYTES) {
      setFileError(t("kp.dashboard.booklet.file_too_large"));
      return;
    }
    upload({ eventId, data: { file } });
  };

  const handleReset = () => {
    if (!confirm(t("kp.dashboard.booklet.reset_confirm"))) return;
    reset({ eventId });
  };

  const isBusy = isUploading || isResetting;

  return (
    <Stack gap="sm">
      <div>
        <Title order={4}>{t("kp.dashboard.booklet.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("kp.dashboard.booklet.requirements")}
        </Text>
      </div>
      <Group align="flex-start" gap="xl" wrap="wrap">
        <Paper
          withBorder
          radius="sm"
          w={PREVIEW_WIDTH}
          maw="100%"
          style={{ overflow: "hidden" }}
        >
          {preview ? (
            <Image
              src={`data:image/png;base64,${preview.png_base64}`}
              alt={t("kp.dashboard.booklet.preview_alt")}
            />
          ) : (
            <Skeleton h={(PREVIEW_WIDTH * 210) / 148.5} />
          )}
        </Paper>
        <Stack gap="sm" style={{ flex: "1 1 240px" }}>
          <Text size="sm">
            {background
              ? background.filename
              : t("kp.dashboard.booklet.default_design")}
          </Text>
          <Group gap="sm">
            <RepickableFileButton
              accept={PDF_UPLOAD_ACCEPT}
              onChange={handleFile}
            >
              {(props) => (
                <Button
                  {...props}
                  disabled={isBusy}
                  loading={isUploading}
                  leftSection={<IconFileUpload size={16} />}
                  variant={background ? "default" : "light"}
                >
                  {background
                    ? t("kp.dashboard.booklet.replace")
                    : t("kp.dashboard.booklet.upload")}
                </Button>
              )}
            </RepickableFileButton>
            {background ? (
              <>
                <Button
                  component="a"
                  href={background.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="default"
                  leftSection={<IconDownload size={16} />}
                >
                  {t("kp.dashboard.booklet.download")}
                </Button>
                <Button
                  color="red"
                  variant="subtle"
                  disabled={isBusy}
                  loading={isResetting}
                  leftSection={<IconRestore size={16} />}
                  onClick={handleReset}
                >
                  {t("kp.dashboard.booklet.reset")}
                </Button>
              </>
            ) : null}
          </Group>
          {fileError ? (
            <Text c="red" size="sm">
              {fileError}
            </Text>
          ) : null}
        </Stack>
      </Group>
    </Stack>
  );
};

export default BookletDesignSection;
