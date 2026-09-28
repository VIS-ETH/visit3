import { useTranslation } from "react-i18next";

export const BoothCard = ({
  status,
  field,
}: {
  status: string;
  field: string;
}) => {
  const { t } = useTranslation();

  return (
    <div>
      <h2>{t("fixture.title")}</h2>
      <p>{t(`fixture.status_${status}`)}</p>
      <p>{t(`fixture.profile_field.${field}`)}</p>
    </div>
  );
};
