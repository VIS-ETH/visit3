import {
  Alert,
  Button,
  Center,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconClock, IconSettings } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import { useGetMyCompany } from "../orval/generated/company/company";
import { useGetUserProfile } from "../orval/generated/user/user";
import CompanyInviteForm from "../components/company/CompanyInviteForm";
import CompanyMembersTable from "../components/company/CompanyMembersTable";
import CompanyProfileBadge from "../components/company/CompanyProfileBadge";
import CompanySettingsModal from "../components/company/CompanySettingsModal";
import ErrorAlert from "../components/ErrorAlert";

const CompanyProfile = () => {
  const { t } = useTranslation();
  const [settingsOpened, setSettingsOpened] = useState(false);
  const [settingsSession, setSettingsSession] = useState(0);

  const { data: userProfile } = useGetUserProfile();
  const { data: company, isError: companyError } = useGetMyCompany();

  const companyName = company?.name ?? userProfile?.company?.name;

  const openSettings = () => {
    setSettingsSession((session) => session + 1);
    setSettingsOpened(true);
  };

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={700} gap="lg">
        <Group justify="space-between" align="center">
          <Title order={2}>{companyName ?? t("company_profile.title")}</Title>
          <Button
            variant="light"
            leftSection={<IconSettings size={16} />}
            onClick={openSettings}
          >
            {t("company_profile.settings_button")}
          </Button>
        </Group>

        <CompanySettingsModal
          key={settingsSession}
          opened={settingsOpened}
          currentName={companyName ?? ""}
          onClose={() => setSettingsOpened(false)}
        />

        {company?.confirmed_at === null ? (
          <Alert
            icon={<IconClock />}
            color="blue"
            variant="light"
            title={t("company_profile.unconfirmed_title")}
          >
            {t("company_profile.unconfirmed_description")}
          </Alert>
        ) : null}

        {companyError ? (
          <ErrorAlert />
        ) : (
          <Paper withBorder p="xl" radius="md">
            <Group justify="space-between" align="center" wrap="wrap">
              <Stack gap={4}>
                <Title order={4}>{t("company_profile.profile_title")}</Title>
                {company ? (
                  <Text c="dimmed" size="sm">
                    {company.profile_complete
                      ? t("company_profile.profile_complete_hint")
                      : t("company_profile.profile_incomplete_hint", {
                          count: company.missing_profile_fields.length,
                        })}
                  </Text>
                ) : null}
              </Stack>
              <Group gap="sm">
                {company ? (
                  <CompanyProfileBadge complete={company.profile_complete} />
                ) : null}
                <Button component={NavLink} to="/company/profile">
                  {t("company_profile.profile_link")}
                </Button>
              </Group>
            </Group>
          </Paper>
        )}

        <CompanyInviteForm
          confirmed={company ? company.confirmed_at !== null : undefined}
        />

        <Title order={3}>{t("company_profile.members_title")}</Title>
        <CompanyMembersTable />
      </Stack>
    </Center>
  );
};
export default CompanyProfile;
