import { Button, Group, Stack, Text } from "@mantine/core";
import type { AxiosRequestConfig } from "axios";
import { useCallback, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../hooks/use-async-action";
import { useWarnOnLeave } from "../../hooks/use-warn-on-leave";
import type {
  BookletPageResponse,
  CompanyProfileResponse,
  IndustryResponse,
  UpdateCompanyProfileRequest,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  companyProfileSchema,
  emptyCompanyProfileFormValues,
  toCompanyProfileFormValues,
  toCompanyProfileRequest,
  type CompanyProfileFormValues,
} from "../../schemas/companyProfileSchema";
import { notifySuccess } from "../../utils/notify";
import { useTranslatedForm } from "../../utils/translator";
import CompanyBillingFields from "./CompanyBillingFields";
import CompanyBookletPage from "./CompanyBookletPage";
import CompanyContactFields from "./CompanyContactFields";
import CompanyDetailsFields from "./CompanyDetailsFields";
import CompanyOfferFields from "./CompanyOfferFields";
import CompanyProfileMissingFields from "./CompanyProfileMissingFields";
import CompanyProfileSection from "./CompanyProfileSection";
import ProfileDraftNotice from "./ProfileDraftNotice";
import { showProfileFieldError } from "./company-profile-fields";
import { useProfileDraft } from "./use-profile-draft";

interface CompanyProfileFormProps {
  profile: CompanyProfileResponse;
  draftScope: string;
  bookletScope: string;
  industries: IndustryResponse[];
  members: UserResponse[];
  logoField: (disabled: boolean) => ReactNode;
  renderBooklet: (
    request: UpdateCompanyProfileRequest,
    options: AxiosRequestConfig,
  ) => Promise<BookletPageResponse>;
  save: (
    request: UpdateCompanyProfileRequest,
  ) => Promise<CompanyProfileResponse>;
}

const CompanyProfileForm = ({
  profile,
  draftScope,
  bookletScope,
  industries,
  members,
  logoField,
  renderBooklet,
  save,
}: CompanyProfileFormProps) => {
  const { t } = useTranslation();

  const lastSavedRef = useRef<string | null>(null);

  const form = useTranslatedForm<typeof companyProfileSchema>(
    companyProfileSchema,
    {
      initialValues: emptyCompanyProfileFormValues,
      onValuesChange: () => {
        lastSavedRef.current = null;
      },
    },
  );

  const applyValues = useCallback(
    (values: CompanyProfileFormValues) => {
      form.setInitialValues(values);
      form.setValues(values);
      form.resetDirty(values);
      form.clearErrors();
    },
    [form],
  );

  const { restored, clearDraft } = useProfileDraft(
    form,
    profile,
    draftScope,
    applyValues,
  );

  const isDirty = form.isDirty();
  useWarnOnLeave(isDirty);

  const { run: submit, isRunning: isSaving } = useAsyncAction(
    async (values: CompanyProfileFormValues) => {
      const request = toCompanyProfileRequest(values);
      const serialized = JSON.stringify(request);
      if (serialized === lastSavedRef.current) return;
      const updated = await save(request);
      clearDraft();
      applyValues(toCompanyProfileFormValues(updated));
      lastSavedRef.current = serialized;
      notifySuccess(t("company_profile_form.save_success"));
    },
    (error) => showProfileFieldError(form, error, t),
  );

  const discard = () => {
    clearDraft();
    applyValues(toCompanyProfileFormValues(profile));
  };

  return (
    <>
      {restored ? <ProfileDraftNotice onDiscard={discard} /> : null}

      <CompanyProfileMissingFields
        fields={profile.missing_profile_fields ?? []}
      />

      <form onSubmit={form.onSubmit((values) => void submit(values))}>
        <Stack gap="lg">
          <CompanyProfileSection
            title={t("company_profile_form.section_company")}
          >
            {logoField(isSaving)}
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
            title={t("company_profile_form.section_booklet")}
          >
            <CompanyBookletPage
              scope={bookletScope}
              ready={form.getInitialValues() !== emptyCompanyProfileFormValues}
              values={form.values}
              logoUrl={profile.logo_url ?? null}
              render={renderBooklet}
            />
          </CompanyProfileSection>

          <CompanyProfileSection
            title={t("company_profile_form.section_billing")}
          >
            <CompanyBillingFields form={form} disabled={isSaving} />
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
              onClick={discard}
            >
              {t("company_profile_form.discard")}
            </Button>
            <Button type="submit" loading={isSaving}>
              {t("company_profile_form.save")}
            </Button>
          </Group>
        </Stack>
      </form>
    </>
  );
};

export default CompanyProfileForm;
