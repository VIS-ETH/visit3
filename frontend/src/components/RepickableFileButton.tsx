import { FileButton, type FileButtonProps } from "@mantine/core";
import { useRef } from "react";

type RepickableFileButtonProps = Omit<FileButtonProps, "resetRef" | "multiple">;

const RepickableFileButton = ({
  onChange,
  ...props
}: RepickableFileButtonProps) => {
  const resetRef = useRef<() => void>(null);

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
