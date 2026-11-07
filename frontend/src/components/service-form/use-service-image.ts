import { useState } from "react";
import {
  useDeleteServiceImage,
  useUploadServiceImage,
} from "../../orval/generated/kp/kp";
import { useWarnOnLeave } from "../../hooks/use-warn-on-leave";

export const useServiceImage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isCleared, setIsCleared] = useState(false);
  const { mutateAsync: upload, isPending: isUploading } =
    useUploadServiceImage();
  const { mutateAsync: remove } = useDeleteServiceImage();
  useWarnOnLeave(isUploading);

  const reset = () => {
    setFile(null);
    setIsCleared(false);
  };

  const chooseFile = (next: File | null) => {
    setFile(next);
    if (next) setIsCleared(false);
  };

  const changeUrl = (url: string) => setIsCleared(!url.trim());

  const save = async (serviceId: string, hasStoredImage: boolean) => {
    if (file) {
      await upload({ serviceId, data: { file } });
    } else if (isCleared && hasStoredImage) {
      await remove({ serviceId });
    }
  };

  return { chooseFile, changeUrl, reset, save };
};
