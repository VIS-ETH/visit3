import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import BackButton from "../components/BackButton";
import { useCurrentUser } from "../context/useCurrentUser";
import {
  getGetCompaniesForKpQueryKey,
  useDeregisterCompanyFromKp,
  useGetCompaniesForKp,
  useGetLatestKp,
  useRegisterCompanyForKp,
} from "../orval/generated/kp/kp";

function formatDate(dateString?: string) {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString();
}

export default function KpJoin() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();

  const {
    data: latestKp,
    isLoading: isLatestLoading,
    isError: isLatestError,
  } = useGetLatestKp();

  const latestEventId = latestKp?.id ?? "";

  const {
    data: registeredCompanies,
    isLoading: isCompaniesLoading,
    isError: isCompaniesError,
  } = useGetCompaniesForKp(latestEventId, {
    query: {
      enabled: !!latestEventId,
    },
  });

  const isRegistered =
    !!user?.company_id &&
    !!registeredCompanies?.some((company) => company.id === user.company_id);

  const invalidateCompanies = async () => {
    if (!latestEventId) return;
    await queryClient.invalidateQueries({
      queryKey: getGetCompaniesForKpQueryKey(latestEventId),
    });
  };

  const { mutate: registerCompany, isPending: isRegistering } =
    useRegisterCompanyForKp({
      mutation: {
        onSuccess: async () => {
          await invalidateCompanies();
          notifications.show({
            color: "green",
            title: t("kp.join.register_success_title"),
            message: t("kp.join.register_success_message"),
          });
        },
      },
    });

  const { mutate: deregisterCompany, isPending: isDeregistering } =
    useDeregisterCompanyFromKp({
      mutation: {
        onSuccess: async () => {
          await invalidateCompanies();
          notifications.show({
            color: "green",
            title: t("kp.join.deregister_success_title"),
            message: t("kp.join.deregister_success_message"),
          });
        },
      },
    });

  const isLoading = isLatestLoading || (isCompaniesLoading && !!latestEventId);
  const isSubmitting = isRegistering || isDeregistering;

  const handleRegister = () => {
    if (!latestEventId) return;
    registerCompany({ eventId: latestEventId });
  };

  const handleDeregister = () => {
    if (!latestEventId) return;
    deregisterCompany({ eventId: latestEventId });
  };

  return (
    <Stack gap="md">
      <BackButton to="/kp" />
      <Title order={2}>{t("kp.join.title")}</Title>
      <Text>{t("kp.join.description")}</Text>

      {isLoading ? (
        <Center py="md">
          <Loader />
        </Center>
      ) : null}

      {(isLatestError || isCompaniesError) && !isLoading ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.join.error")}
        </Alert>
      ) : null}

      {!isLoading && !isLatestError ? (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Title order={4}>{t("kp.join.current_event")}</Title>
            {latestKp ? (
              <>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.year")}:
                  </Text>
                  {latestKp.year}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.registration_window")}:
                  </Text>
                  {formatDate(latestKp.registration_open)} -{" "}
                  {formatDate(latestKp.registration_end)}
                </Text>
                <Text>
                  <Text span fw={600}>
                    {t("kp.join.event_date")}:
                  </Text>
                  {formatDate(latestKp.event_date)}
                </Text>

                <Group mt="xs">
                  {isRegistered ? (
                    <Button
                      color="red"
                      variant="light"
                      onClick={handleDeregister}
                      loading={isSubmitting}
                    >
                      {t("kp.join.deregister_button")}
                    </Button>
                  ) : (
                    <Button onClick={handleRegister} loading={isSubmitting}>
                      {t("kp.join.register_button")}
                    </Button>
                  )}
                </Group>
              </>
            ) : (
              <Text c="dimmed">{t("kp.join.no_event")}</Text>
            )}
          </Stack>
        </Card>
      ) : null}
    </Stack>
  );
}
