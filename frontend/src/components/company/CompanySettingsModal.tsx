import { Button, Group, Modal, Stack, TextInput } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useAsyncAction } from "../../hooks/use-async-action";
import {
  getGetMyCompanyQueryKey,
  updateMyCompany,
} from "../../orval/generated/company/company";
import { getGetUserProfileQueryKey } from "../../orval/generated/user/user";
import { companySchema } from "../../schemas/companySchema";
import { notifySuccess } from "../../utils/notify";
import { useTranslatedForm } from "../../utils/translator";

interface CompanySettingsModalProps {
  opened: boolean;
  currentName: string;
  onClose: () => void;
}

const CompanySettingsModal = ({
  opened,
  currentName,
  onClose,
}: CompanySettingsModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const form = useTranslatedForm<typeof companySchema>(companySchema, {
    initialValues: { name: currentName },
  });

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async (name: string) => {
      await updateMyCompany({ name });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getGetMyCompanyQueryKey() }),
        queryClient.invalidateQueries({
          queryKey: getGetUserProfileQueryKey(),
        }),
      ]);
      onClose();
      notifySuccess(t("company_profile.settings_success"));
    },
  );

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (!isSaving) onClose();
      }}
      title={t("company_profile.settings_title")}
      centered
      closeOnEscape={!isSaving}
      closeOnClickOutside={!isSaving}
      withCloseButton={!isSaving}
    >
      <form onSubmit={form.onSubmit((v) => void save(v.name.trim()))}>
        <Stack gap="md">
          <TextInput
            label={t("company_profile.name_label")}
            placeholder={t("company_profile.name_placeholder")}
            {...form.getInputProps("name")}
            disabled={isSaving}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose} disabled={isSaving}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={isSaving} disabled={!form.isValid()}>
              {t("company_profile.save")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CompanySettingsModal;
