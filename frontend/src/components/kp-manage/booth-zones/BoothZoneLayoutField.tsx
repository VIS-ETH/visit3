import { Anchor, Button, Group, Image, Stack, Text } from "@mantine/core";
import { IconExternalLink, IconTrash, IconUpload } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
  LAYOUT_UPLOAD_ACCEPT,
  isPdfSource,
} from "../../../utils/upload-formats";
import RepickableFileButton from "../../RepickableFileButton";
import type { useZoneLayoutFile } from "./use-zone-layout-file";

const StoredLayoutPreview = ({ url }: { url: string }) => {
  const { t } = useTranslation();
  if (isPdfSource(url)) {
    return (
      <Anchor href={url} target="_blank" rel="noopener noreferrer">
        <Group gap={6} wrap="nowrap">
          <IconExternalLink size={16} />
          <Text size="sm">{t("kp.manage.zone_layout_open_pdf")}</Text>
        </Group>
      </Anchor>
    );
  }
  return (
    <Image
      alt={t("kp.manage.zone_layout_preview_alt")}
      fit="contain"
      mah={200}
      radius="sm"
      src={url}
    />
  );
};

const BoothZoneLayoutField = ({
  layout,
  disabled,
}: {
  layout: ReturnType<typeof useZoneLayoutFile>;
  disabled: boolean;
}) => {
  const { t } = useTranslation();
  const hasLayout = Boolean(layout.file ?? layout.storedUrl);

  return (
    <Stack gap="xs">
      <Text fw={500} size="sm">
        {t("kp.manage.zone_layout_file")}
      </Text>
      <Text c="dimmed" size="xs">
        {t("kp.manage.zone_layout_allowed_formats")}
      </Text>
      <Group align="center" gap="sm">
        <RepickableFileButton
          accept={LAYOUT_UPLOAD_ACCEPT}
          onChange={layout.choose}
        >
          {(props) => (
            <Button
              {...props}
              disabled={disabled}
              leftSection={<IconUpload size={16} />}
              variant={hasLayout ? "default" : "light"}
            >
              {hasLayout
                ? t("kp.manage.zone_layout_replace")
                : t("kp.manage.zone_layout_upload")}
            </Button>
          )}
        </RepickableFileButton>
        {hasLayout ? (
          <Button
            color="red"
            disabled={disabled}
            leftSection={<IconTrash size={16} />}
            onClick={layout.clear}
            variant="subtle"
          >
            {t("kp.manage.zone_layout_remove")}
          </Button>
        ) : null}
      </Group>
      {layout.file ? (
        <Text size="sm">{layout.file.name}</Text>
      ) : layout.storedUrl ? (
        <StoredLayoutPreview url={layout.storedUrl} />
      ) : (
        <Text c="dimmed" size="sm">
          {t("kp.manage.zone_layout_none")}
        </Text>
      )}
      {layout.error !== null ? (
        <Text c="red" size="sm">
          {layout.error}
        </Text>
      ) : null}
    </Stack>
  );
};

export default BoothZoneLayoutField;
