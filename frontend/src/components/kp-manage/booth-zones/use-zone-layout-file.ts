import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useDeleteBoothZoneLayoutFile,
  useUploadBoothZoneLayoutFile,
} from "../../../orval/generated/kp/kp";
import { useWarnOnLeave } from "../../../hooks/use-warn-on-leave";
import { isAllowedLayoutType } from "../../../utils/upload-formats";

export const useZoneLayoutFile = (storedUrl: string | null) => {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [isCleared, setIsCleared] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { mutateAsync: upload, isPending: isUploading } =
    useUploadBoothZoneLayoutFile();
  const { mutateAsync: remove } = useDeleteBoothZoneLayoutFile();
  useWarnOnLeave(isUploading);

  const choose = (next: File | null) => {
    if (next && !isAllowedLayoutType(next.type)) {
      setError(t("kp.manage.zone_layout_file_invalid"));
      return;
    }
    setError(null);
    setFile(next);
    if (next) setIsCleared(false);
  };

  const clear = () => {
    setError(null);
    setFile(null);
    setIsCleared(true);
  };

  const save = async (boothZoneId: string) => {
    if (file) {
      await upload({ boothZoneId, data: { file } });
    } else if (isCleared && storedUrl) {
      await remove({ boothZoneId });
    }
  };

  return {
    file,
    error,
    storedUrl: isCleared ? null : storedUrl,
    choose,
    clear,
    save,
  };
};
