import { Button, Image, Paper, Skeleton, Stack } from "@mantine/core";
import { IconEye, IconEyeOff } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { usePreviewEventNametag } from "../../orval/generated/kp/kp";
import ErrorAlert from "../ErrorAlert";

const PREVIEW_WIDTH = 390;
const NAMETAG_WIDTH_MM = 90;
const NAMETAG_HEIGHT_MM = 54;

const NametagPreview = ({
  eventId,
  hasBackground,
}: {
  eventId: string;
  hasBackground: boolean;
}) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const previewQuery = usePreviewEventNametag(eventId, {
    query: { enabled: isOpen && hasBackground },
  });
  const preview = previewQuery.data;

  return (
    <Stack gap="xs" align="flex-start">
      <Button
        variant="default"
        disabled={!hasBackground}
        leftSection={isOpen ? <IconEyeOff size={16} /> : <IconEye size={16} />}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen
          ? t("kp.dashboard.exports.hide_preview")
          : t("kp.dashboard.exports.show_preview")}
      </Button>
      {isOpen && hasBackground ? (
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
              alt={t("kp.dashboard.exports.preview_alt")}
            />
          ) : previewQuery.isError ? (
            <ErrorAlert />
          ) : (
            <Skeleton
              h={(PREVIEW_WIDTH * NAMETAG_HEIGHT_MM) / NAMETAG_WIDTH_MM}
            />
          )}
        </Paper>
      ) : null}
    </Stack>
  );
};

export default NametagPreview;
