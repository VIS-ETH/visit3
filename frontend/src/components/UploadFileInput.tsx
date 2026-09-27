import { FileInput, type FileInputProps } from "@mantine/core";
import { useState } from "react";
import { UPLOADS_AVAILABLE } from "../utils/uploads";
import UploadsUnavailableModal from "./UploadsUnavailableModal";

const UploadFileInput = (props: FileInputProps) => {
  const [noticeOpened, setNoticeOpened] = useState(false);

  if (UPLOADS_AVAILABLE) return <FileInput {...props} />;

  return (
    <>
      <FileInput {...props} onClick={() => setNoticeOpened(true)} />
      <UploadsUnavailableModal
        opened={noticeOpened}
        onClose={() => setNoticeOpened(false)}
      />
    </>
  );
};

export default UploadFileInput;
