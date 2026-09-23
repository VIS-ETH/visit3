import { NumberInput } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const BoothNumberCell = ({
  boothNr,
  disabled,
  onSave,
}: {
  boothNr: number | null;
  disabled: boolean;
  onSave: (boothNr: number | null) => void;
}) => {
  const { t } = useTranslation();
  const [value, setValue] = useState<string | number>(boothNr ?? "");

  useEffect(() => {
    setValue(boothNr ?? "");
  }, [boothNr]);

  const commit = () => {
    const next = value === "" ? null : Number(value);
    if (next === boothNr) return;
    if (next !== null && (!Number.isInteger(next) || next < 1)) {
      setValue(boothNr ?? "");
      return;
    }
    onSave(next);
  };

  return (
    <NumberInput
      aria-label={t("kp.manage.booking_booth_nr")}
      disabled={disabled}
      hideControls
      min={1}
      onBlur={commit}
      onChange={setValue}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
        if (event.key === "Escape") setValue(boothNr ?? "");
      }}
      size="xs"
      value={value}
      w={80}
    />
  );
};

export default BoothNumberCell;
