import { TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useTranslation } from "react-i18next";

export const BoothCard = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h2>{t("fixture.missing_title")}</h2>
      <p>
        Every booth comes with a table and two chairs, and the power socket is
        billed separately.
      </p>
      <img alt="Photo of a booth" src="/booth.png" />
      <TextInput aria-label="Booth number" error="Pick a booth number" />
      <button
        type="button"
        onClick={() => notifications.show({ message: "Booth saved" })}
      >
        {t("fixture.save")}
      </button>
    </div>
  );
};
