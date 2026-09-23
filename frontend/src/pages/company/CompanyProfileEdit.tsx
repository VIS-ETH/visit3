import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import BackButton from "../../components/BackButton";
import CompanyBillingFields from "../../components/company/CompanyBillingFields";
import CompanyContactFields from "../../components/company/CompanyContactFields";
import CompanyDetailsFields from "../../components/company/CompanyDetailsFields";
import CompanyLogoField from "../../components/company/CompanyLogoField";
import CompanyOfferFields from "../../components/company/CompanyOfferFields";
import CompanyProfileBadge from "../../components/company/CompanyProfileBadge";
import CompanyProfileMissingFields from "../../components/company/CompanyProfileMissingFields";
import CompanyProfileSection from "../../components/company/CompanyProfileSection";
import CompanyShippingFields from "../../components/company/CompanyShippingFields";
import { useCurrentUser } from "../../context/useCurrentUser";
import {
  getGetMyCompanyProfileQueryKey,
  getGetMyCompanyQueryKey,
  useGetMyCompanyMembers,
  useGetMyCompanyProfile,
  useUpdateMyCompanyProfile,
} from "../../orval/generated/company/company";
import { useListIndustryCatalogue } from "../../orval/generated/industry/industry";
import {
  companyProfileSchema,
  emptyCompanyProfileFormValues,
  toCompanyProfileFormValues,
  toCompanyProfileRequest,
  type CompanyProfileFormValues,
} from "../../schemas/companyProfileSchema";
import { useTranslatedForm } from "../../utils/translator";

const CompanyProfileEdit = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();

  const {
    data: profile,
    isLoading,
    isError,
  } = useGetMyCompanyProfile({ query: { retry: false } });
  const { data: industries = [] } = useListIndustryCatalogue();
  const { data: members = [] } = useGetMyCompanyMembers({
    query: { enabled: user?.user_confirmed === true },
  });

  const form = useTranslatedForm<typeof companyProfileSchema>(
    companyProfileSchema,
    { initialValues: emptyCompanyProfileFormValues },
  );

  const loadedProfileIdRef = useRef<string | null>(null);

  const applyValues = useCallback(
    (values: CompanyProfileFormValues) => {
      form.setInitialValues(values);
      form.setValues(values);
      form.resetDirty(values);
      form.clearErrors();
    },
    [form],
  );

  useEffect(() => {
    if (!profile || loadedProfileIdRef.current === profile.company_id) return;
    loadedProfileIdRef.current = profile.company_id;
    applyValues(toCompanyProfileFormValues(profile));
  }, [profile, applyValues]);

  const isDirty = form.isDirty();

  useEffect(() => {
    if (!isDirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isDirty]);

  const { mutate: save, isPending: isSaving } = useUpdateMyCompanyProfile({
    mutation: {
      onSuccess: async (updated) => {
        queryClient.setQueryData(getGetMyCompanyProfileQueryKey(), updated);
        await queryClient.invalidateQueries({
          queryKey: getGetMyCompanyQueryKey(),
        });
        applyValues(toCompanyProfileFormValues(updated));
        notifications.show({
          color: "green",
          message: t("company_profile_form.save_success"),
        });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError || !profile) {
    return (
      <Center py="xl">
        <Alert icon={<IconAlertCircle />} color="red" title={t("error.title")}>
          {t("company_profile_form.load_error")}
        </Alert>
      </Center>
    );
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={860} gap="lg" px="md">
        <Group justify="space-between" align="center">
          <Group gap="xs" align="center">
            <BackButton to="/company" />
            <Title order={2}>{t("company_profile_form.title")}</Title>
          </Group>
          <CompanyProfileBadge complete={profile.profile_complete === true} />
        </Group>
        <Text c="dimmed" size="sm">
          {t("company_profile_form.subtitle")}
        </Text>

        <CompanyProfileMissingFields
          fields={profile.missing_profile_fields ?? []}
        />

        <form
          onSubmit={form.onSubmit((values) =>
            save({ data: toCompanyProfileRequest(values) }),
          )}
        >
          <Stack gap="lg">
            <CompanyProfileSection
              title={t("company_profile_form.section_company")}
            >
              <CompanyLogoField
                logoUrl={profile.logo_url ?? null}
                disabled={isSaving}
              />
              <CompanyDetailsFields
                form={form}
                disabled={isSaving}
                industries={industries}
              />
            </CompanyProfileSection>

            <CompanyProfileSection
              title={t("company_profile_form.section_offers")}
            >
              <CompanyOfferFields form={form} disabled={isSaving} />
            </CompanyProfileSection>

            <CompanyProfileSection
              title={t("company_profile_form.section_contact")}
            >
              <CompanyContactFields
                form={form}
                disabled={isSaving}
                members={members}
              />
            </CompanyProfileSection>

            <CompanyProfileSection
              title={t("company_profile_form.section_billing")}
            >
              <CompanyBillingFields form={form} disabled={isSaving} />
            </CompanyProfileSection>

            <CompanyProfileSection
              title={t("company_profile_form.section_shipping")}
            >
              <CompanyShippingFields form={form} disabled={isSaving} />
            </CompanyProfileSection>

            <Group justify="flex-end" gap="sm" align="center">
              {isDirty ? (
                <Text c="dimmed" size="sm">
                  {t("company_profile_form.unsaved")}
                </Text>
              ) : null}
              <Button
                variant="default"
                disabled={!isDirty || isSaving}
                onClick={() => applyValues(toCompanyProfileFormValues(profile))}
              >
                {t("company_profile_form.discard")}
              </Button>
              <Button type="submit" loading={isSaving} disabled={isSaving}>
                {t("company_profile_form.save")}
              </Button>
            </Group>
          </Stack>
        </form>
      </Stack>
    </Center>
  );
};

export default CompanyProfileEdit;
