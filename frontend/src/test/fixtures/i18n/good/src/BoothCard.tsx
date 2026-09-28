import { TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useTranslation } from "react-i18next";

export const BoothCard = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h2>{t("fixture.title")}</h2>
      <p>{t("fixture.body")}</p>
      <img alt={t("fixture.booth_photo_alt")} src="/booth.png" />
      <TextInput
        aria-label={t("fixture.booth_number_label")}
        error={t("fixture.booth_number_error")}
      />
      <button
        type="button"
        onClick={() => notifications.show({ message: t("fixture.saved") })}
      >
        {t("fixture.save")}
      </button>
    </div>
  );
};
