import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  getGetCompanyProfileQueryKey,
  useDeleteCompanyProfileLogo,
  useUploadCompanyProfileLogo,
} from "../../orval/generated/company/company";
import type { CompanyProfileResponse } from "../../orval/generated/fastAPI.schemas";
import CompanyLogoControls from "./CompanyLogoControls";

interface CompanyLogoFieldForStaffProps {
  companyId: string;
  logoUrl: string | null;
  disabled: boolean;
}

const CompanyLogoFieldForStaff = ({
  companyId,
  logoUrl,
  disabled,
}: CompanyLogoFieldForStaffProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const storeProfile = (profile: CompanyProfileResponse) => {
    queryClient.setQueryData(getGetCompanyProfileQueryKey(companyId), profile);
  };

  const { mutate: upload, isPending: isUploading } =
    useUploadCompanyProfileLogo({
      mutation: {
        onSuccess: (profile) => {
          storeProfile(profile);
          notifications.show({
            color: "green",
            message: t("company_profile_form.logo_upload_success"),
          });
        },
      },
    });

  const { mutate: removeLogo, isPending: isRemoving } =
    useDeleteCompanyProfileLogo({
      mutation: {
        onSuccess: (profile) => {
          storeProfile(profile);
          notifications.show({
            color: "green",
            message: t("company_profile_form.logo_remove_success"),
          });
        },
      },
    });

  return (
    <CompanyLogoControls
      logoUrl={logoUrl}
      disabled={disabled}
      isUploading={isUploading}
      isRemoving={isRemoving}
      onUpload={(file) => upload({ companyId, data: { file } })}
      onRemove={() => removeLogo({ companyId })}
    />
  );
};

export default CompanyLogoFieldForStaff;
