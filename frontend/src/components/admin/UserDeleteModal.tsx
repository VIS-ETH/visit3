import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifySuccess } from "../../utils/notify";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getInlineErrorCode, inlineErrorRequest } from "../../api/errors";
import ErrorAlert from "../ErrorAlert";
import { useAsyncAction } from "../../hooks/use-async-action";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getListUsersQueryKey,
  useDeleteUser,
} from "../../orval/generated/user/user";

interface UserDeleteModalProps {
  user: UserResponse | null;
  onClose: () => void;
}

const UserDeleteModal = ({ user, onClose }: UserDeleteModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    if (user) setErrorCode(null);
  }, [user]);

  const { mutateAsync: deleteUser } = useDeleteUser({
    request: inlineErrorRequest,
  });

  const { run: remove, isRunning: isPending } = useAsyncAction(
    async (userId: string) => {
      setErrorCode(null);
      await deleteUser({ userId });
      await queryClient.invalidateQueries({
        queryKey: getListUsersQueryKey(),
      });
      notifySuccess(t("user_management.delete_modal.deleted"));
      onClose();
    },
    (error) => setErrorCode(getInlineErrorCode(error)),
  );

  return (
    <Modal
      centered
      closeOnClickOutside={!isPending}
      closeOnEscape={!isPending}
      onClose={() => {
        if (!isPending) onClose();
      }}
      opened={user !== null}
      title={t("user_management.delete_modal.title")}
      withCloseButton={!isPending}
    >
      <Stack gap="sm">
        <Text>
          {t("user_management.delete_modal.message", {
            email: user?.email ?? "",
          })}
        </Text>
        <Text c="red" fw={600}>
          {t("user_management.delete_modal.irreversible")}
        </Text>
        {errorCode ? <ErrorAlert>{t(errorCode)}</ErrorAlert> : null}
        <Group justify="flex-end" mt="md">
          <Button disabled={isPending} onClick={onClose} variant="default">
            {t("user_management.delete_modal.cancel")}
          </Button>
          <Button
            color="red"
            loading={isPending}
            onClick={() => {
              if (user) void remove(user.id);
            }}
          >
            {t("user_management.delete_modal.confirm")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default UserDeleteModal;
