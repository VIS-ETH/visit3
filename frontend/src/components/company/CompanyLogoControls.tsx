import { Button, Group, Image, Stack, Text } from "@mantine/core";
import { IconPhotoUp, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  isAllowedLogoType,
  LOGO_UPLOAD_ACCEPT,
} from "../../utils/upload-formats";
import RepickableFileButton from "../RepickableFileButton";

const MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024;

interface CompanyLogoControlsProps {
  logoUrl: string | null;
  disabled: boolean;
  isUploading: boolean;
  isRemoving: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
}

const CompanyLogoControls = ({
  logoUrl,
  disabled,
  isUploading,
  isRemoving,
  onUpload,
  onRemove,
}: CompanyLogoControlsProps) => {
  const { t } = useTranslation();
  const [fileError, setFileError] = useState<string | null>(null);
  const isBusy = disabled || isUploading || isRemoving;

  const handleFile = (file: File | null) => {
    setFileError(null);
    if (!file) return;
    if (!isAllowedLogoType(file.type) || file.size > MAX_LOGO_SIZE_BYTES) {
      setFileError(t("company_profile_form.logo_invalid"));
      return;
    }
    onUpload(file);
  };

  return (
    <Stack gap="xs">
      <Text fw={500} size="sm">
        {t("company_profile_form.logo")}
      </Text>
      <Text c="dimmed" size="xs">
        {t("company_profile_form.logo_hint")}
      </Text>
      {logoUrl ? (
        <Image
          alt={t("company_profile_form.logo_alt")}
          src={logoUrl}
          fit="contain"
          h={96}
          w="auto"
        />
      ) : null}
      <Group gap="sm">
        <RepickableFileButton accept={LOGO_UPLOAD_ACCEPT} onChange={handleFile}>
          {(props) => (
            <Button
              {...props}
              disabled={isBusy}
              loading={isUploading}
              leftSection={<IconPhotoUp size={16} />}
              variant={logoUrl ? "default" : "light"}
            >
              {logoUrl
                ? t("company_profile_form.logo_replace")
                : t("company_profile_form.logo_upload")}
            </Button>
          )}
        </RepickableFileButton>
        {logoUrl ? (
          <Button
            color="red"
            variant="subtle"
            disabled={isBusy}
            loading={isRemoving}
            leftSection={<IconTrash size={16} />}
            onClick={onRemove}
          >
            {t("company_profile_form.logo_remove")}
          </Button>
        ) : null}
      </Group>
      {fileError ? (
        <Text c="red" size="sm">
          {fileError}
        </Text>
      ) : null}
    </Stack>
  );
};

export default CompanyLogoControls;
