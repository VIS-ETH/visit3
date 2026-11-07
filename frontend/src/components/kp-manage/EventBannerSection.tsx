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
import { IconPhotoUp, IconRestore } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getGetEventBannerQueryKey,
  getGetLatestKpQueryKey,
  useGetEventBanner,
  useResetEventBanner,
  useUploadEventBanner,
} from "../../orval/generated/kp/kp";
import { LOGO_UPLOAD_ACCEPT } from "../../utils/upload-formats";
import { useWarnOnLeave } from "../../hooks/use-warn-on-leave";
import { eventBannerImage } from "../home/kontaktparty-banner";
import { useAsyncAction } from "../../hooks/use-async-action";
import ErrorAlert from "../ErrorAlert";
import RepickableFileButton from "../RepickableFileButton";

const MAX_BANNER_SIZE_BYTES = 5 * 1024 * 1024;
const PREVIEW_WIDTH = 480;
const PREVIEW_SIZES = `${PREVIEW_WIDTH}px`;

const EventBannerSection = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [fileError, setFileError] = useState<string | null>(null);
  const { data: banner, isPending, isError } = useGetEventBanner(eventId);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetEventBannerQueryKey(eventId),
      }),
      queryClient.invalidateQueries({ queryKey: getGetLatestKpQueryKey() }),
    ]);

  const { mutateAsync: uploadBanner } = useUploadEventBanner();
  const { mutateAsync: resetBanner } = useResetEventBanner();
  const { run: upload, isRunning: isUploading } = useAsyncAction(
    async (file: File) => {
      await uploadBanner({ eventId, data: { file } });
      await refresh();
    },
  );
  const { run: reset, isRunning: isResetting } = useAsyncAction(async () => {
    await resetBanner({ eventId });
    await refresh();
  });
  useWarnOnLeave(isUploading);

  const handleFile = (file: File | null) => {
    setFileError(null);
    if (!file) return;
    if (file.size > MAX_BANNER_SIZE_BYTES) {
      setFileError(t("kp.dashboard.banner.file_too_large"));
      return;
    }
    void upload(file);
  };

  const handleReset = () => {
    if (!confirm(t("kp.dashboard.banner.reset_confirm"))) return;
    void reset();
  };

  const image = eventBannerImage(banner);
  const isBusy = isUploading || isResetting;

  return (
    <Stack gap="sm">
      <div>
        <Title order={4}>{t("kp.dashboard.banner.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("kp.dashboard.banner.requirements")}
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
          {isError ? (
            <ErrorAlert />
          ) : isPending ? (
            <Skeleton
              radius={0}
              style={{ aspectRatio: `${image.width} / ${image.height}` }}
            />
          ) : (
            <Image
              src={image.src}
              srcSet={image.srcSet}
              sizes={PREVIEW_SIZES}
              width={image.width}
              height={image.height}
              alt={t("kp.dashboard.banner.preview_alt")}
              h="auto"
              fit="contain"
              style={{ aspectRatio: `${image.width} / ${image.height}` }}
            />
          )}
        </Paper>
        <Stack gap="sm" style={{ flex: "1 1 240px" }}>
          <Text size="sm">
            {banner
              ? t("kp.dashboard.banner.custom_banner")
              : t("kp.dashboard.banner.default_banner")}
          </Text>
          <Group gap="sm">
            <RepickableFileButton
              accept={LOGO_UPLOAD_ACCEPT}
              onChange={handleFile}
            >
              {(props) => (
                <Button
                  {...props}
                  disabled={isBusy}
                  loading={isUploading}
                  leftSection={<IconPhotoUp size={16} />}
                  variant={banner ? "default" : "light"}
                >
                  {banner
                    ? t("kp.dashboard.banner.replace")
                    : t("kp.dashboard.banner.upload")}
                </Button>
              )}
            </RepickableFileButton>
            {banner ? (
              <Button
                color="red"
                variant="subtle"
                disabled={isBusy}
                loading={isResetting}
                leftSection={<IconRestore size={16} />}
                onClick={handleReset}
              >
                {t("kp.dashboard.banner.reset")}
              </Button>
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

export default EventBannerSection;
