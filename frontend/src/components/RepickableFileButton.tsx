import { FileButton, type FileButtonProps } from "@mantine/core";
import { useRef, useState } from "react";
import { UPLOADS_AVAILABLE } from "../utils/uploads";
import UploadsUnavailableModal from "./UploadsUnavailableModal";

type RepickableFileButtonProps = Omit<FileButtonProps, "resetRef" | "multiple">;

const RepickableFileButton = ({
  onChange,
  ...props
}: RepickableFileButtonProps) => {
  const resetRef = useRef<() => void>(null);
  const [noticeOpened, setNoticeOpened] = useState(false);

  if (!UPLOADS_AVAILABLE) {
    return (
      <>
        {props.children({ onClick: () => setNoticeOpened(true) })}
        <UploadsUnavailableModal
          opened={noticeOpened}
          onClose={() => setNoticeOpened(false)}
        />
      </>
    );
  }

  return (
    <FileButton
      {...props}
      resetRef={resetRef}
      onChange={(file) => {
        resetRef.current?.();
        onChange(file);
      }}
    />
  );
};

export default RepickableFileButton;
