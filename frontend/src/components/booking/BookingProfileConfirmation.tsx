import {
  Alert,
  Card,
  Center,
  Checkbox,
  Group,
  List,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
  Button,
} from "@mantine/core";
import { IconAlertCircle, IconBuilding, IconPencil } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import type {
  CompanyMemberResult,
  CompanyProfileResponse,
  MyCompanyResponse,
} from "../../orval/generated/fastAPI.schemas";
import { useGetMyCompanyProfile } from "../../orval/generated/company/company";
import { getFullName } from "../../utils/display";
import { COMPANY_PROFILE_PATH } from "../../utils/navigation";

const joinProfileParts = (parts: (string | null | undefined)[]) =>
  parts
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));

const contactLines = (contact: CompanyMemberResult | null | undefined) =>
  contact
    ? joinProfileParts([
        getFullName(contact.first_name, contact.last_name),
        contact.email,
        contact.phone_number,
      ])
    : [];

const billingAddressLines = (profile: CompanyProfileResponse) =>
  joinProfileParts([
    profile.billing_company_name,
    joinProfileParts([
      profile.billing_street,
      profile.billing_house_number,
    ]).join(" "),
    joinProfileParts([profile.billing_postal_code, profile.billing_city]).join(
      " ",
    ),
    profile.billing_country,
  ]);

function ProfileSummaryField({
  label,
  lines,
}: {
  label: string;
  lines: string[];
}) {
  const { t } = useTranslation();
  return (
    <Stack gap={2}>
      <Text c="dimmed" size="xs">
        {label}
      </Text>
      {lines.length === 0 ? (
        <Text size="sm">{t("kp.booking.profile_value_missing")}</Text>
      ) : (
        lines.map((line) => (
          <Text key={line} size="sm">
            {line}
          </Text>
        ))
      )}
    </Stack>
  );
}

export default function BookingProfileConfirmation({
  returnPath,
  company,
  isConfirmed,
  onConfirmedChange,
}: {
  returnPath: string;
  company: MyCompanyResponse | undefined;
  isConfirmed: boolean;
  onConfirmedChange: (isConfirmed: boolean) => void;
}) {
  const { t } = useTranslation();
  const { data: profile, isLoading } = useGetMyCompanyProfile();
  const missingFields = company?.missing_profile_fields ?? [];

  if (isLoading || !profile || !company) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Card withBorder radius="md" p="lg" mt="xs">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Group gap="sm">
            <IconBuilding size={20} />
            <Title order={4}>{t("kp.booking.profile_title")}</Title>
          </Group>
          <Button
            component={NavLink}
            to={`${COMPANY_PROFILE_PATH}?next=${encodeURIComponent(returnPath)}`}
            variant="light"
            leftSection={<IconPencil size={16} />}
          >
            {t("kp.booking.profile_edit")}
          </Button>
        </Group>
        <Text c="dimmed" size="sm">
          {t("kp.booking.profile_description")}
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <ProfileSummaryField
            label={t("kp.booking.profile_company")}
            lines={joinProfileParts([company.name, profile.brand_name])}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_contact")}
            lines={contactLines(profile.kp_contact_user)}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_general_contact")}
            lines={joinProfileParts([
              profile.general_email,
              profile.general_phone,
            ])}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_billing_address")}
            lines={billingAddressLines(profile)}
          />
          <ProfileSummaryField
            label={t("kp.booking.profile_industries")}
            lines={(profile.industries ?? []).map((industry) => industry.name)}
          />
        </SimpleGrid>
        {missingFields.length > 0 ? (
          <Alert icon={<IconAlertCircle />} color="yellow">
            <Stack gap="xs">
              <Text size="sm">
                {company.profile_bookable
                  ? t("kp.booking.profile_incomplete_deferred")
                  : t("kp.booking.profile_incomplete")}
              </Text>
              <List size="sm" withPadding>
                {missingFields.map((field) => (
                  <List.Item key={field}>
                    {t(`kp.booking.profile_field.${field}`)}
                  </List.Item>
                ))}
              </List>
            </Stack>
          </Alert>
        ) : null}
        <Checkbox
          checked={isConfirmed}
          disabled={!company.profile_bookable}
          label={t("kp.booking.profile_confirm_checkbox")}
          onChange={(event) => onConfirmedChange(event.currentTarget.checked)}
        />
      </Stack>
    </Card>
  );
}
