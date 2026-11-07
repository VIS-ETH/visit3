import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import type { VenueLayoutResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getGetEventVenueQueryKey,
  getListVenueLayoutsQueryKey,
  useReplaceVenueBooths,
  useReplaceVenueZoneShapes,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { useWarnOnLeave } from "../../hooks/use-warn-on-leave";
import { notifySuccess } from "../../utils/notify";
import {
  boothsRequest,
  draftFromLayout,
  isSameDraft,
  shapesRequest,
  type VenueDraft,
} from "./venue-draft";
import { exceedsRequestLimit } from "./venue-limits";

export function useVenueLayoutSave(
  layout: VenueLayoutResponse,
  draft: VenueDraft,
  onDirtyChange?: (isDirty: boolean) => void,
) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [savedDraft, setSavedDraft] = useState<VenueDraft>(() =>
    draftFromLayout(layout),
  );
  const [saveErrorCode, setSaveErrorCode] = useState<string | null>(null);
  const { mutateAsync: replaceShapes } = useReplaceVenueZoneShapes();
  const { mutateAsync: replaceBooths } = useReplaceVenueBooths();

  const isDirty = !isSameDraft(draft, savedDraft);

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  useWarnOnLeave(isDirty);

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async () => {
      setSaveErrorCode(null);
      const shapes = shapesRequest(draft);
      const booths = boothsRequest(draft);
      if ([shapes, booths].some(exceedsRequestLimit)) {
        setSaveErrorCode("kp.venue.map_too_large");
        return;
      }
      await replaceShapes({ layoutId: layout.id, data: shapes });
      const saved = await replaceBooths({ layoutId: layout.id, data: booths });
      setSavedDraft(draftFromLayout(saved));
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getListVenueLayoutsQueryKey(layout.event_id),
        }),
        queryClient.invalidateQueries({
          queryKey: getGetEventVenueQueryKey(layout.event_id),
        }),
      ]);
      notifySuccess(t("kp.venue.saved"));
    },
    (error) => setSaveErrorCode(getApiErrorCode(error) ?? "error.internal"),
  );

  return { save, isSaving, isDirty, saveErrorCode };
}
