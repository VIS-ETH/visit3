import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  getGetMyCompanyProfileQueryKey,
  getGetMyCompanyQueryKey,
  useDeleteMyCompanyProfileLogo,
  useUploadMyCompanyProfileLogo,
} from "../../orval/generated/company/company";
import type { CompanyProfileResponse } from "../../orval/generated/fastAPI.schemas";
import CompanyLogoControls from "./CompanyLogoControls";

interface CompanyLogoFieldProps {
  logoUrl: string | null;
  disabled: boolean;
}

const CompanyLogoField = ({ logoUrl, disabled }: CompanyLogoFieldProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const storeProfile = async (profile: CompanyProfileResponse) => {
    queryClient.setQueryData(getGetMyCompanyProfileQueryKey(), profile);
    await queryClient.invalidateQueries({
      queryKey: getGetMyCompanyQueryKey(),
    });
  };

  const { mutate: upload, isPending: isUploading } =
    useUploadMyCompanyProfileLogo({
      mutation: {
        onSuccess: async (profile) => {
          await storeProfile(profile);
          notifications.show({
            color: "green",
            message: t("company_profile_form.logo_upload_success"),
          });
        },
      },
    });

  const { mutate: removeLogo, isPending: isRemoving } =
    useDeleteMyCompanyProfileLogo({
      mutation: {
        onSuccess: async (profile) => {
          await storeProfile(profile);
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
      onUpload={(file) => upload({ data: { file } })}
      onRemove={() => removeLogo()}
    />
  );
};

export default CompanyLogoField;
