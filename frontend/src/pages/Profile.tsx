import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconSettings } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  getGetUserProfileQueryKey,
  useGetUserProfile,
  useUpdateUserProfile,
} from "../orval/generated/user/user";
import type { UpdateUserProfileRequest } from "../orval/generated/fastAPI.schemas";
import { profileSchema } from "../schemas/profileSchema";
import { useTranslatedForm } from "../utils/translator";
import { useState } from "react";
import { getDisplayName } from "../utils/display";

function normalizeProfileValue(value?: string | null) {
  const trimmed = value?.trim() ?? "";
  return trimmed.length > 0 ? trimmed : null;
}

type NormalizedProfile = {
  firstName: string | null;
  lastName: string | null;
  phoneNumber: string | null;
};

function toNormalizedProfile(values: {
  firstName?: string | null;
  lastName?: string | null;
  phoneNumber?: string | null;
}): NormalizedProfile {
  return {
    firstName: normalizeProfileValue(values.firstName),
    lastName: normalizeProfileValue(values.lastName),
    phoneNumber: normalizeProfileValue(values.phoneNumber),
  };
}

function changedProfileFields(
  next: NormalizedProfile,
  current: NormalizedProfile,
): UpdateUserProfileRequest {
  const changes: UpdateUserProfileRequest = {};
  if (next.firstName !== current.firstName) changes.first_name = next.firstName;
  if (next.lastName !== current.lastName) changes.last_name = next.lastName;
  if (next.phoneNumber !== current.phoneNumber) {
    changes.phone_number = next.phoneNumber;
  }
  return changes;
}

const Profile = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [settingsOpened, setSettingsOpened] = useState(false);
  const { data: user, isLoading, isError } = useGetUserProfile();

  const form = useTranslatedForm<typeof profileSchema>(profileSchema, {
    initialValues: {
      firstName: "",
      lastName: "",
      phoneNumber: "",
    },
  });

  const { mutate: updateUserProfile, isPending: isUpdating } =
    useUpdateUserProfile({
      mutation: {
        onSuccess: async () => {
          await queryClient.invalidateQueries({
            queryKey: getGetUserProfileQueryKey(),
          });
          setSettingsOpened(false);
          notifications.show({
            color: "green",
            title: t("profile.edit.success_title"),
            message: t("profile.edit.success_message"),
          });
        },
      },
    });

  const openSettings = () => {
    const values = {
      firstName: user?.first_name ?? "",
      lastName: user?.last_name ?? "",
      phoneNumber: user?.phone_number ?? "",
    };
    form.setInitialValues(values);
    form.setValues(values);
    form.clearErrors();
    setSettingsOpened(true);
  };

  const nextProfile = toNormalizedProfile(form.values);
  const currentProfile = toNormalizedProfile({
    firstName: user?.first_name,
    lastName: user?.last_name,
    phoneNumber: user?.phone_number,
  });

  const hasChanges =
    Object.keys(changedProfileFields(nextProfile, currentProfile)).length > 0;
  const disableSave = isUpdating || !hasChanges || !form.isValid();

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError || !user) {
    return (
      <Center py="xl">
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("profile.load_error")}
        </Alert>
      </Center>
    );
  }

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={700} gap="lg">
        <Group justify="space-between" align="center">
          <Title order={2}>{t("profile.title")}</Title>
          <Button
            variant="light"
            leftSection={<IconSettings size={16} />}
            onClick={openSettings}
          >
            {t("profile.edit.button")}
          </Button>
        </Group>

        <Modal
          opened={settingsOpened}
          onClose={() => {
            if (!isUpdating) {
              setSettingsOpened(false);
            }
          }}
          title={t("profile.edit.title")}
          centered
          closeOnEscape={!isUpdating}
          closeOnClickOutside={!isUpdating}
          withCloseButton={!isUpdating}
        >
          <form
            onSubmit={form.onSubmit((values) => {
              const changes = changedProfileFields(
                toNormalizedProfile(values),
                currentProfile,
              );

              if (Object.keys(changes).length === 0) {
                setSettingsOpened(false);
                return;
              }

              updateUserProfile({ data: changes });
            })}
          >
            <Stack gap="md">
              <TextInput
                label={t("profile.edit.first_name")}
                {...form.getInputProps("firstName")}
              />
              <TextInput
                label={t("profile.edit.last_name")}
                {...form.getInputProps("lastName")}
              />
              <TextInput
                label={t("profile.edit.phone_number")}
                {...form.getInputProps("phoneNumber")}
              />

              <Group justify="flex-end" mt="sm">
                <Button
                  type="button"
                  variant="default"
                  onClick={() => setSettingsOpened(false)}
                  disabled={isUpdating}
                >
                  {t("profile.edit.cancel")}
                </Button>
                <Button
                  type="submit"
                  loading={isUpdating}
                  disabled={disableSave}
                >
                  {t("profile.edit.save")}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>

        <Paper withBorder p="md" radius="md">
          <Stack gap="sm">
            <Text>
              <Text span fw={600}>
                {t("profile.name")}:{" "}
              </Text>
              {getDisplayName(user.first_name, user.last_name)}
            </Text>
            <Text>
              <Text span fw={600}>
                {t("profile.email")}:{" "}
              </Text>
              {user.email}
            </Text>
            <Text>
              <Text span fw={600}>
                {t("profile.phone")}:{" "}
              </Text>
              {user.phone_number ?? "-"}
            </Text>
          </Stack>
        </Paper>
      </Stack>
    </Center>
  );
};
export default Profile;
