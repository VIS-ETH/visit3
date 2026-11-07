import { NumberInput } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../hooks/use-async-action";

const BoothNumberCell = ({
  boothNr,
  onSave,
}: {
  boothNr: number | null;
  onSave: (boothNr: number | null) => Promise<unknown>;
}) => {
  const { t } = useTranslation();
  const [value, setValue] = useState<string | number>(boothNr ?? "");
  const revert = () => setValue(boothNr ?? "");
  const { run: save, isRunning: isSaving } = useAsyncAction(onSave, revert);

  useEffect(() => {
    setValue(boothNr ?? "");
  }, [boothNr]);

  const commit = () => {
    const next = value === "" ? null : Number(value);
    if (next === boothNr) return;
    if (next !== null && (!Number.isInteger(next) || next < 1)) {
      revert();
      return;
    }
    void save(next);
  };

  return (
    <NumberInput
      allowDecimal={false}
      aria-label={t("kp.manage.booking_booth_nr")}
      disabled={isSaving}
      hideControls
      min={1}
      onBlur={commit}
      onChange={setValue}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
        if (event.key === "Escape") revert();
      }}
      size="xs"
      value={value}
      w={80}
    />
  );
};

export default BoothNumberCell;
