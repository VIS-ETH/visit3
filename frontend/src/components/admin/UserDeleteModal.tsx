import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
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

  const { mutate: remove, isPending } = useDeleteUser({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getListUsersQueryKey(),
        });
        notifications.show({
          color: "green",
          message: t("user_management.delete_modal.deleted"),
        });
        onClose();
      },
      onError: (error) => {
        setErrorCode(getApiErrorCode(error) ?? "server.error");
      },
    },
  });

  return (
    <Modal
      centered
      closeOnClickOutside={!isPending}
      closeOnEscape={!isPending}
      onClose={onClose}
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
        {errorCode ? (
          <Alert
            color="red"
            icon={<IconAlertCircle />}
            title={t("error.title")}
          >
            {t(errorCode)}
          </Alert>
        ) : null}
        <Group justify="flex-end" mt="md">
          <Button disabled={isPending} onClick={onClose} variant="default">
            {t("user_management.delete_modal.cancel")}
          </Button>
          <Button
            color="red"
            loading={isPending}
            onClick={() => {
              if (!user) return;
              setErrorCode(null);
              remove({ userId: user.id });
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
