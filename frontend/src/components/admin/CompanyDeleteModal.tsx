import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifySuccess } from "../../utils/notify";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import ErrorAlert from "../ErrorAlert";
import {
  getSearchCompaniesQueryKey,
  useDeleteCompanyKeepUsers,
  useDeleteCompanyWithUsers,
} from "../../orval/generated/company/company";

interface CompanyDeleteModalProps {
  company: { id: string; name: string; usersCount: number } | null;
  onClose: () => void;
}

const CompanyDeleteModal = ({ company, onClose }: CompanyDeleteModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    if (company) setErrorCode(null);
  }, [company]);

  const mutationOptions = {
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: getSearchCompaniesQueryKey(),
      });
      notifySuccess(t("company_management.delete_modal.deleted"));
      onClose();
    },
    onError: (error: unknown) => {
      setErrorCode(getApiErrorCode(error) ?? "server.error");
    },
  };

  const requestOptions = { quietStatuses: [409] };

  const { mutate: deleteKeepUsers, isPending: isDeletingKeepUsers } =
    useDeleteCompanyKeepUsers({
      mutation: mutationOptions,
      request: requestOptions,
    });
  const { mutate: deleteWithUsers, isPending: isDeletingWithUsers } =
    useDeleteCompanyWithUsers({
      mutation: mutationOptions,
      request: requestOptions,
    });

  const isPending = isDeletingKeepUsers || isDeletingWithUsers;
  const hasUsers = (company?.usersCount ?? 0) > 0;

  return (
    <Modal
      centered
      closeOnClickOutside={!isPending}
      closeOnEscape={!isPending}
      onClose={onClose}
      opened={company !== null}
      title={t("company_management.delete_modal.title")}
      withCloseButton={!isPending}
    >
      <Stack gap="sm">
        <Text>
          {t("company_management.delete_modal.message", {
            name: company?.name ?? "",
          })}
        </Text>
        <Text c="red" fw={600}>
          {t("company_management.delete_modal.irreversible")}
        </Text>
        {errorCode ? <ErrorAlert>{t(errorCode)}</ErrorAlert> : null}
        <Group justify="flex-end" mt="md">
          <Button disabled={isPending} onClick={onClose} variant="default">
            {t("company_management.delete_modal.cancel")}
          </Button>
          <Button
            color="yellow"
            disabled={isPending}
            loading={isDeletingKeepUsers}
            onClick={() => {
              if (!company) return;
              setErrorCode(null);
              deleteKeepUsers({ companyId: company.id });
            }}
          >
            {t("company_management.delete_modal.keep_users")}
          </Button>
          {hasUsers ? (
            <Button
              color="red"
              disabled={isPending}
              loading={isDeletingWithUsers}
              onClick={() => {
                if (!company) return;
                setErrorCode(null);
                deleteWithUsers({ companyId: company.id });
              }}
            >
              {t("company_management.delete_modal.delete_with_users")}
            </Button>
          ) : null}
        </Group>
      </Stack>
    </Modal>
  );
};

export default CompanyDeleteModal;
