import { Card, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import { useGetLatestKp } from "../orval/generated/kp/kp";
import { formatKpDisplayDate } from "../utils/kp-utils";

const Detail = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => (
  <Text>
    <Text span fw={600}>
      {label}:
    </Text>{" "}
    {children}
  </Text>
);

const KpJoin = () => {
  const { t } = useTranslation();

  const { data: latestKp, isPending, isError } = useGetLatestKp();

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <Title order={2}>{t("kp.join.title")}</Title>

      {isError ? (
        <ErrorAlert>{t("kp.join.error")}</ErrorAlert>
      ) : isPending ? (
        <PageLoader />
      ) : (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Title order={4}>{t("kp.join.current_event")}</Title>
            {latestKp ? (
              <>
                <Detail label={t("kp.join.name")}>{latestKp.name}</Detail>
                <Detail label={t("kp.join.registration_window")}>
                  {formatKpDisplayDate(latestKp.registration_open)} -{" "}
                  {formatKpDisplayDate(latestKp.registration_end)}
                </Detail>
                <Detail label={t("kp.join.finalization_deadline")}>
                  {formatKpDisplayDate(latestKp.finalization_deadline)}
                </Detail>
                <Detail label={t("kp.join.nametags_deadline")}>
                  {formatKpDisplayDate(latestKp.nametags_deadline)}
                </Detail>
                <Detail label={t("kp.join.event_date")}>
                  {formatKpDisplayDate(latestKp.event_date)}
                </Detail>
              </>
            ) : (
              <Text c="dimmed">{t("kp.join.no_event")}</Text>
            )}
          </Stack>
        </Card>
      )}
    </Stack>
  );
};
export default KpJoin;
