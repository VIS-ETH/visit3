import { Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  getGetUserProfileQueryKey,
  useRequestEmailChange,
} from "../orval/generated/user/user";
import { emailChangeSchema } from "../schemas/profileSchema";
import { useTranslatedForm } from "../utils/translator";

interface EmailChangeModalProps {
  opened: boolean;
  onClose: () => void;
  currentEmail: string;
}

const EmailChangeModal = ({
  opened,
  onClose,
  currentEmail,
}: EmailChangeModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const form = useTranslatedForm<typeof emailChangeSchema>(emailChangeSchema, {
    initialValues: { email: "" },
  });

  const { reset } = form;

  useEffect(() => {
    if (opened) reset();
  }, [opened, reset]);

  const { mutate: requestEmailChange, isPending } = useRequestEmailChange({
    mutation: {
      onSuccess: async (updated) => {
        await queryClient.invalidateQueries({
          queryKey: getGetUserProfileQueryKey(),
        });
        notifications.show({
          color: "green",
          title: t("profile.email_change.sent_title"),
          message: t("profile.email_change.sent_message", {
            email: updated.pending_email,
          }),
        });
        onClose();
      },
    },
  });

  const unchanged =
    form.values.email.trim().toLowerCase() === currentEmail.toLowerCase();

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (!isPending) onClose();
      }}
      title={t("profile.email_change.title")}
      centered
      closeOnEscape={!isPending}
      closeOnClickOutside={!isPending}
      withCloseButton={!isPending}
    >
      <form
        onSubmit={form.onSubmit((values) =>
          requestEmailChange({ data: { email: values.email.trim() } }),
        )}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            {t("profile.email_change.description", { email: currentEmail })}
          </Text>
          <TextInput
            autoComplete="email"
            disabled={isPending}
            label={t("profile.email_change.email")}
            {...form.getInputProps("email")}
          />
          <Group justify="flex-end" mt="sm">
            <Button
              type="button"
              variant="default"
              onClick={onClose}
              disabled={isPending}
            >
              {t("profile.edit.cancel")}
            </Button>
            <Button type="submit" loading={isPending} disabled={unchanged}>
              {t("profile.email_change.submit")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default EmailChangeModal;
