import {
  Button,
  FileButton,
  Group,
  Image,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import { IconEye, IconPhotoUp, IconTrash } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useState } from "react";

interface ImageUploadInputProps {
  value: string;
  onChange: (value: string) => void;
  onFileChange?: (file: File | null) => void;
  label: string;
  disabled?: boolean;
  previewAlt: string;
  uploadLabel: string;
  replaceLabel: string;
  previewLabel: string;
  clearLabel: string;
  currentFileLabel: string;
  invalidFileMessage: string;
  maxSizeBytes?: number;
  error?: ReactNode;
}

const DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024;

const readFileAsDataUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

const ImageUploadInput = ({
  value,
  onChange,
  onFileChange,
  label,
  disabled = false,
  previewAlt,
  uploadLabel,
  replaceLabel,
  previewLabel,
  clearLabel,
  currentFileLabel,
  invalidFileMessage,
  maxSizeBytes = DEFAULT_MAX_SIZE_BYTES,
  error,
}: ImageUploadInputProps) => {
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [previewOpened, setPreviewOpened] = useState(false);

  const handleFileChange = async (nextFile: File | null) => {
    setFileError(null);
    if (!nextFile) return;
    if (!nextFile.type.startsWith("image/") || nextFile.size > maxSizeBytes) {
      setFileError(invalidFileMessage);
      return;
    }
    setFileName(nextFile.name);
    onFileChange?.(nextFile);
    onChange(await readFileAsDataUrl(nextFile));
  };

  const handleClear = () => {
    setFileError(null);
    setFileName(null);
    setPreviewOpened(false);
    onFileChange?.(null);
    onChange("");
  };

  const hasImage = Boolean(value.trim());

  return (
    <>
      <Modal
        centered
        opened={previewOpened}
        onClose={() => setPreviewOpened(false)}
        title={fileName ?? currentFileLabel}
        size="lg"
      >
        <Image
          alt={previewAlt}
          fit="contain"
          mah="70vh"
          src={value.trim()}
          w="100%"
        />
      </Modal>
      <Stack gap="xs">
        <Text fw={500} size="sm">
          {label}
        </Text>
        <Group align="center" gap="sm">
          <FileButton accept="image/*" onChange={handleFileChange}>
            {(props) => (
              <Button
                {...props}
                disabled={disabled}
                leftSection={<IconPhotoUp size={16} />}
                variant={hasImage ? "default" : "light"}
              >
                {hasImage ? replaceLabel : uploadLabel}
              </Button>
            )}
          </FileButton>
          {hasImage ? (
            <>
              <Text size="sm">{fileName ?? currentFileLabel}</Text>
              <Button
                disabled={disabled}
                leftSection={<IconEye size={16} />}
                onClick={() => setPreviewOpened(true)}
                variant="default"
              >
                {previewLabel}
              </Button>
              <Button
                color="red"
                disabled={disabled}
                leftSection={<IconTrash size={16} />}
                onClick={handleClear}
                variant="subtle"
              >
                {clearLabel}
              </Button>
            </>
          ) : null}
        </Group>
        {fileError || error ? (
          <Text c="red" size="sm">
            {fileError ?? error}
          </Text>
        ) : null}
      </Stack>
    </>
  );
};

export default ImageUploadInput;
