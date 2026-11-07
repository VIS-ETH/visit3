import {
  Badge,
  Button,
  Group,
  Loader,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import {
  IconDownload,
  IconRefresh,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../../hooks/use-async-action";
import {
  KpEventServiceRequirementType,
  type ServiceRequirementResponse,
} from "../../../orval/generated/fastAPI.schemas";
import {
  getBookingRequirementFileDownloadUrl,
  useGetBookingRequirementFile,
  useGetBookingRequirementText,
} from "../../../orval/generated/kp/kp";
import { REQUIREMENT_TEXT_MAX_LENGTH } from "../../../utils/kp-utils";
import { bookingRequirementElementId } from "../../../utils/navigation";
import { requirementTypeLabel } from "../../../utils/requirement-type";
import {
  acceptForRequirement,
  allowedFormatsLabel,
} from "../../../utils/upload-formats";
import ErrorAlert from "../../ErrorAlert";
import UploadFileInput from "../../UploadFileInput";
import type { PendingRequirementChange } from "./requirement-changes";

type RequirementDraft = {
  text?: string;
  file?: File | null;
};

interface RequirementEditorProps {
  bookingServiceId: string;
  editable: boolean;
  isSaving: boolean;
  onChange: (
    bookingServiceId: string,
    requirementId: string,
    change: PendingRequirementChange | null,
  ) => void;
  onCompletionChange: (
    bookingServiceId: string,
    requirementId: string,
    isComplete: boolean,
  ) => void;
  pendingChange?: PendingRequirementChange;
  requirement: ServiceRequirementResponse;
  serviceName: string;
}

const RequirementEditor = ({
  bookingServiceId,
  editable,
  isSaving,
  onChange,
  onCompletionChange,
  pendingChange,
  requirement,
  serviceName,
}: RequirementEditorProps) => {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<RequirementDraft>({});
  const isText = requirement.type === KpEventServiceRequirementType.text;
  const target = {
    bookingServiceId,
    requirementId: requirement.id,
    serviceName,
    requirementName: requirement.name,
  };
  const {
    data: requirementFile,
    isFetching,
    isError: isFileError,
    refetch: refetchFile,
  } = useGetBookingRequirementFile(bookingServiceId, requirement.id, {
    query: { enabled: !isText, retry: false },
  });
  const {
    data: requirementText,
    isFetched: isTextFetched,
    isError: isTextError,
  } = useGetBookingRequirementText(bookingServiceId, requirement.id, {
    query: { enabled: isText, retry: false },
  });
  const requirementTextValue = requirementText?.text_value ?? "";
  const draftText = draft.text ?? "";

  useEffect(() => {
    if (!isText || !isTextFetched || isTextError || draft.text !== undefined)
      return;
    setDraft((current) => ({
      ...current,
      text:
        pendingChange?.kind === "text"
          ? pendingChange.text
          : requirementTextValue,
    }));
  }, [
    draft.text,
    isText,
    isTextError,
    isTextFetched,
    pendingChange,
    requirementTextValue,
  ]);
  useEffect(() => {
    if (isText) return;
    const pendingFile =
      pendingChange?.kind === "file" ? pendingChange.file : null;
    if ((draft.file ?? null) === pendingFile) return;
    setDraft((current) => ({ ...current, file: pendingFile }));
  }, [draft.file, isText, pendingChange]);
  useEffect(() => {
    const isComplete = isText
      ? Boolean(requirementTextValue.trim())
      : Boolean(requirementFile);
    onCompletionChange(bookingServiceId, requirement.id, isComplete);
  }, [
    bookingServiceId,
    isText,
    onCompletionChange,
    requirement.id,
    requirementFile,
    requirementTextValue,
  ]);

  const { run: download, isRunning: isDownloading } = useAsyncAction(
    async () => {
      const response = await getBookingRequirementFileDownloadUrl(
        bookingServiceId,
        requirement.id,
      );
      window.location.assign(response.url);
    },
  );

  const changeText = (text: string) => {
    const trimmed = text.trim();
    setDraft((current) => ({ ...current, text }));
    onChange(
      bookingServiceId,
      requirement.id,
      trimmed !== requirementTextValue
        ? { ...target, kind: "text", text: trimmed }
        : null,
    );
  };

  const changeFile = (file: File | null) => {
    setDraft((current) => ({ ...current, file }));
    onChange(
      bookingServiceId,
      requirement.id,
      file ? { ...target, kind: "file", file } : null,
    );
  };

  const toggleDelete = () => {
    setDraft((current) => ({ ...current, file: null }));
    onChange(
      bookingServiceId,
      requirement.id,
      pendingChange?.kind === "delete_file"
        ? null
        : { ...target, kind: "delete_file" },
    );
  };

  const renderInput = () => {
    if (isText) {
      if (isTextError) return <ErrorAlert />;
      return (
        <Stack gap={4} style={{ flex: "1 1 520px" }}>
          <Textarea
            autosize
            maxRows={14}
            minRows={6}
            disabled={!editable}
            maxLength={REQUIREMENT_TEXT_MAX_LENGTH}
            placeholder={t("kp.booking_manage.text_placeholder")}
            size="sm"
            value={draftText}
            onChange={(event) => changeText(event.currentTarget.value)}
          />
        </Stack>
      );
    }
    if (isFileError) {
      return (
        <Button
          leftSection={<IconRefresh size={16} />}
          onClick={() => {
            void refetchFile();
          }}
          size="sm"
          variant="light"
        >
          {t("kp.booking_manage.retry_file_load")}
        </Button>
      );
    }
    return (
      <UploadFileInput
        disabled={!editable}
        accept={acceptForRequirement(requirement.type)}
        description={allowedFormatsLabel(requirement.type, t)}
        leftSection={<IconUpload size={16} />}
        placeholder={
          requirementFile
            ? t("kp.booking_manage.replace_file")
            : t("kp.booking_manage.upload_file")
        }
        size="sm"
        style={{ flex: "1 1 260px" }}
        value={draft.file ?? null}
        onChange={changeFile}
      />
    );
  };

  return (
    <Stack
      gap="xs"
      id={bookingRequirementElementId(requirement.id)}
      py="sm"
      style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}
    >
      <Group justify="space-between" align="flex-start" gap="md">
        <div style={{ minWidth: 220, flex: "0 1 34%" }}>
          <Group gap="xs">
            <Text size="sm" fw={600}>
              {requirement.name}
            </Text>
            <Badge variant="light" size="xs">
              {requirementTypeLabel(requirement.type, t)}
            </Badge>
          </Group>
          <Text c="dimmed" size="xs">
            {requirement.description}
          </Text>
          {!isText ? (
            <Text c="dimmed" size="xs" mt={4}>
              {isFetching
                ? t("kp.booking_manage.checking_file")
                : isFileError
                  ? t("kp.booking_manage.file_load_error")
                  : requirementFile
                    ? requirementFile.stored_file.original_filename
                    : t("kp.booking_manage.no_file")}
            </Text>
          ) : null}
        </div>

        <Group align="flex-end" gap="xs" style={{ flex: "1 1 420px" }}>
          {renderInput()}

          {!isText && requirementFile ? (
            <Button
              size="xs"
              variant="subtle"
              leftSection={<IconDownload size={14} />}
              loading={isDownloading}
              onClick={() => {
                void download();
              }}
            >
              {t("kp.booking_manage.download_file")}
            </Button>
          ) : null}
          {!isText && requirementFile && editable ? (
            <Button
              color="red"
              size="xs"
              variant="subtle"
              leftSection={<IconTrash size={14} />}
              onClick={toggleDelete}
            >
              {pendingChange?.kind === "delete_file"
                ? t("kp.booking_manage.undo_delete_file")
                : t("kp.booking_manage.delete_file")}
            </Button>
          ) : null}
          {isSaving ? (
            <Badge
              leftSection={<Loader color="blue" size={10} />}
              variant="light"
            >
              {isText
                ? t("kp.booking_manage.saving")
                : t("kp.booking_manage.uploading")}
            </Badge>
          ) : pendingChange ? (
            <Badge variant="light">
              {t("kp.booking_manage.pending_change")}
            </Badge>
          ) : null}
        </Group>
      </Group>
    </Stack>
  );
};

export default RequirementEditor;
