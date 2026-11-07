import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../../hooks/use-async-action";
import {
  getGetBookingRequirementFileQueryKey,
  getGetBookingRequirementTextQueryKey,
  useDeleteBookingRequirementFile,
  useDeleteBookingRequirementText,
  useUploadBookingRequirementFile,
  useUpsertBookingRequirementText,
} from "../../../orval/generated/kp/kp";
import { notifyError, notifySuccess } from "../../../utils/notify";
import {
  changeKey,
  requirementChangeKey,
  type PendingRequirementChange,
  type RequirementCompletion,
} from "./requirement-changes";

export const useRequirementChanges = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingChanges, setPendingChanges] = useState<
    Record<string, PendingRequirementChange>
  >({});
  const [completion, setCompletion] = useState<RequirementCompletion>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const { mutateAsync: uploadFile } = useUploadBookingRequirementFile();
  const { mutateAsync: saveText } = useUpsertBookingRequirementText();
  const { mutateAsync: deleteFile } = useDeleteBookingRequirementFile();
  const { mutateAsync: deleteText } = useDeleteBookingRequirementText();

  const changeList = Object.values(pendingChanges);

  const setChange = useCallback(
    (
      bookingServiceId: string,
      requirementId: string,
      change: PendingRequirementChange | null,
    ) => {
      setPendingChanges((current) => {
        const next = { ...current };
        const key = requirementChangeKey(bookingServiceId, requirementId);
        if (change === null) {
          delete next[key];
        } else {
          next[key] = change;
        }
        return next;
      });
    },
    [],
  );

  const setCompletionFor = useCallback(
    (bookingServiceId: string, requirementId: string, isComplete: boolean) => {
      setCompletion((current) => {
        const key = requirementChangeKey(bookingServiceId, requirementId);
        if (current[key] === isComplete) return current;
        return { ...current, [key]: isComplete };
      });
    },
    [],
  );

  const discardAll = () => setPendingChanges({});

  const saveChange = async (change: PendingRequirementChange) => {
    const ids = {
      bookingServiceId: change.bookingServiceId,
      requirementId: change.requirementId,
    };
    if (change.kind === "text") {
      await (change.text
        ? saveText({ ...ids, data: { text_value: change.text } })
        : deleteText(ids));
      await queryClient.invalidateQueries({
        queryKey: getGetBookingRequirementTextQueryKey(
          ids.bookingServiceId,
          ids.requirementId,
        ),
      });
      return;
    }
    if (change.kind === "file") {
      await uploadFile({ ...ids, data: { file: change.file } });
    } else {
      await deleteFile(ids);
    }
    await queryClient.invalidateQueries({
      queryKey: getGetBookingRequirementFileQueryKey(
        ids.bookingServiceId,
        ids.requirementId,
      ),
    });
  };

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (changes: PendingRequirementChange[]) => {
      const savedKeys: string[] = [];
      let failedCount = 0;
      try {
        for (const change of changes) {
          setSavingKey(changeKey(change));
          try {
            await saveChange(change);
            savedKeys.push(changeKey(change));
          } catch {
            failedCount += 1;
          }
        }
      } finally {
        setSavingKey(null);
      }
      setPendingChanges((current) => {
        const next = { ...current };
        for (const key of savedKeys) delete next[key];
        return next;
      });
      if (failedCount === 0) {
        notifySuccess(t("kp.booking_manage.requirements_saved"));
        return true;
      }
      notifyError(
        t(
          savedKeys.length > 0
            ? "kp.booking_manage.requirements_partially_saved"
            : "kp.booking_manage.requirements_save_failed",
          { failed: failedCount, saved: savedKeys.length },
        ),
      );
      return false;
    },
  );

  return {
    pendingChanges,
    changeList,
    completion,
    savingKey,
    isSaving,
    setChange,
    setCompletionFor,
    discardAll,
    save,
  };
};

export type RequirementChanges = ReturnType<typeof useRequirementChanges>;
