import { Center, Group, Stack, Text, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";
import { useScrollToHash } from "../../hooks/use-scroll-to-hash";
import BackButton from "../../components/BackButton";
import ErrorAlert from "../../components/ErrorAlert";
import PageLoader from "../../components/PageLoader";
import CompanyLogoField from "../../components/company/CompanyLogoField";
import CompanyProfileBadge from "../../components/company/CompanyProfileBadge";
import CompanyProfileForm from "../../components/company/CompanyProfileForm";
import {
  getGetMyCompanyProfileQueryKey,
  getGetMyCompanyQueryKey,
  previewMyCompanyBookletPage,
  updateMyCompanyProfile,
  useGetMyCompanyMembers,
  useGetMyCompanyProfile,
} from "../../orval/generated/company/company";
import type { UpdateCompanyProfileRequest } from "../../orval/generated/fastAPI.schemas";
import { useListIndustryCatalogue } from "../../orval/generated/industry/industry";
import { getSafeNextPath } from "../../utils/navigation";

const CompanyProfileEdit = () => {
  const { t } = useTranslation();
  useScrollToHash();
  const queryClient = useQueryClient();
  const location = useLocation();
  const backPath = getSafeNextPath(location.search) ?? "/company";

  const {
    data: profile,
    isLoading,
    isError,
  } = useGetMyCompanyProfile({ query: { retry: false } });
  const { data: industries = [] } = useListIndustryCatalogue();
  const { data: members = [] } = useGetMyCompanyMembers();

  const save = async (request: UpdateCompanyProfileRequest) => {
    const updated = await updateMyCompanyProfile(request);
    queryClient.setQueryData(getGetMyCompanyProfileQueryKey(), updated);
    await queryClient.invalidateQueries({
      queryKey: getGetMyCompanyQueryKey(),
    });
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
            <BackButton to={backPath} />
            <Title order={2}>{t("company_profile_form.title")}</Title>
          </Group>
          <CompanyProfileBadge complete={profile.profile_complete === true} />
        </Group>
        <Text c="dimmed" size="sm">
          {t("company_profile_form.subtitle")}
        </Text>

        <CompanyProfileForm
          profile={profile}
          draftScope="me"
          bookletScope="me"
          industries={industries}
          members={members}
          logoField={(disabled) => (
            <CompanyLogoField
              logoUrl={profile.logo_url ?? null}
              disabled={disabled}
            />
          )}
          renderBooklet={previewMyCompanyBookletPage}
          save={save}
        />
      </Stack>
    </Center>
  );
};

export default CompanyProfileEdit;
