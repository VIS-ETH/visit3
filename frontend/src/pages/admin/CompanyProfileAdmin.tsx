import { Center, Group, Stack, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import BackButton from "../../components/BackButton";
import ErrorAlert from "../../components/ErrorAlert";
import PageLoader from "../../components/PageLoader";
import CompanyLogoFieldForStaff from "../../components/company/CompanyLogoFieldForStaff";
import CompanyProfileBadge from "../../components/company/CompanyProfileBadge";
import CompanyProfileForm from "../../components/company/CompanyProfileForm";
import {
  getGetCompanyProfileQueryKey,
  previewCompanyBookletPage,
  updateCompanyProfile,
  useGetCompanyProfile,
  useGetCompanyUsers,
} from "../../orval/generated/company/company";
import type { UpdateCompanyProfileRequest } from "../../orval/generated/fastAPI.schemas";
import { useListIndustryCatalogue } from "../../orval/generated/industry/industry";

const CompanyProfileAdmin = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { companyId = "" } = useParams<{ companyId: string }>();

  const {
    data: profile,
    isLoading,
    isError,
  } = useGetCompanyProfile(companyId, {
    query: { enabled: companyId !== "", retry: false },
  });
  const { data: industries = [] } = useListIndustryCatalogue();
  const { data: members = [] } = useGetCompanyUsers(companyId, {
    query: { enabled: companyId !== "" },
  });

  const save = async (request: UpdateCompanyProfileRequest) => {
    const updated = await updateCompanyProfile(companyId, request);
    queryClient.setQueryData(getGetCompanyProfileQueryKey(companyId), updated);
    return updated;
  };

  if (isLoading) {
    return <PageLoader />;
  }

  if (isError || !profile) {
    return (
      <Center py="xl">
        <ErrorAlert>{t("company_profile_form.load_error")}</ErrorAlert>
      </Center>
    );
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={860} gap="lg" px="md">
        <Group justify="space-between" align="center">
          <Group gap="xs" align="center">
            <BackButton to="/company-management" />
            <Title order={2}>{t("company_management.profile_title")}</Title>
          </Group>
          <CompanyProfileBadge complete={profile.profile_complete === true} />
        </Group>

        <CompanyProfileForm
          profile={profile}
          draftScope="staff"
          bookletScope={companyId}
          industries={industries}
          members={members}
          logoField={(disabled) => (
            <CompanyLogoFieldForStaff
              companyId={companyId}
              logoUrl={profile.logo_url ?? null}
              disabled={disabled}
            />
          )}
          renderBooklet={(request, options) =>
            previewCompanyBookletPage(companyId, request, options)
          }
          save={save}
        />
      </Stack>
    </Center>
  );
};

export default CompanyProfileAdmin;
