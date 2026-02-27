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
import { useUpdateMyCompany } from "../orval/generated/company/company";
import { profileSchema } from "../schemas/profileSchema";
import { companySchema } from "../schemas/companySchema";
import { useTranslatedForm } from "../utils/translator";
import { useState } from "react";

function getFullName(firstName?: string | null, lastName?: string | null) {
  const fullName = `${firstName ?? ""} ${lastName ?? ""}`.trim();
  return fullName.length > 0 ? fullName : "-";
}

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

function hasMeaningfulChanges(
  next: NormalizedProfile,
  current: NormalizedProfile
) {
  return (
    next.firstName !== current.firstName ||
    next.lastName !== current.lastName ||
    next.phoneNumber !== current.phoneNumber
  );
}

export default function Profile() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [settingsOpened, setSettingsOpened] = useState(false);
  const [companySettingsOpened, setCompanySettingsOpened] = useState(false);
  const { data: user, isLoading, isError } = useGetUserProfile();

  const form = useTranslatedForm<typeof profileSchema>(profileSchema, {
    initialValues: {
      firstName: "",
      lastName: "",
      phoneNumber: "",
    },
    validateInputOnChange: true,
  });

  const companyForm = useTranslatedForm<typeof companySchema>(companySchema, {
    initialValues: {
      name: "",
    },
    validateInputOnChange: true,
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

  const { mutate: updateCompany, isPending: isUpdatingCompany } =
    useUpdateMyCompany({
      mutation: {
        onSuccess: async () => {
          await queryClient.invalidateQueries({
            queryKey: getGetUserProfileQueryKey(),
          });
          setCompanySettingsOpened(false);
          notifications.show({
            color: "green",
            title: t("profile.company_edit.success_title"),
            message: t("profile.company_edit.success_message"),
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

  const openCompanySettings = () => {
    const values = {
      name: user?.company?.name ?? "",
    };
    companyForm.setInitialValues(values);
    companyForm.setValues(values);
    companyForm.clearErrors();
    setCompanySettingsOpened(true);
  };

  const nextProfile = toNormalizedProfile(form.values);
  const currentProfile = toNormalizedProfile({
    firstName: user?.first_name,
    lastName: user?.last_name,
    phoneNumber: user?.phone_number,
  });

  const hasChanges = hasMeaningfulChanges(nextProfile, currentProfile);

  const disableSave = isUpdating || !hasChanges || !form.isValid();
  const disableCompanySave =
    isUpdatingCompany ||
    companyForm.values.name.trim() === user?.company?.name ||
    !companyForm.isValid();

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
              const submittedProfile = toNormalizedProfile(values);

              if (!hasMeaningfulChanges(submittedProfile, currentProfile)) {
                setSettingsOpened(false);
                return;
              }

              updateUserProfile({
                data: {
                  first_name: submittedProfile.firstName,
                  last_name: submittedProfile.lastName,
                  phone_number: submittedProfile.phoneNumber,
                },
              });
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

        <Modal
          opened={companySettingsOpened}
          onClose={() => {
            if (!isUpdatingCompany) {
              setCompanySettingsOpened(false);
            }
          }}
          title={t("profile.company_edit.title")}
          centered
          closeOnEscape={!isUpdatingCompany}
          closeOnClickOutside={!isUpdatingCompany}
          withCloseButton={!isUpdatingCompany}
        >
          <form
            onSubmit={companyForm.onSubmit((values) => {
              updateCompany({
                data: {
                  name: values.name,
                },
              });
            })}
          >
            <Stack>
              <TextInput
                label={t("profile.company_edit.name")}
                placeholder={t("profile.company_edit.name_placeholder")}
                {...companyForm.getInputProps("name")}
                disabled={isUpdatingCompany}
              />

              <Group justify="flex-end" gap="sm">
                <Button
                  type="button"
                  variant="default"
                  onClick={() => setCompanySettingsOpened(false)}
                  disabled={isUpdatingCompany}
                >
                  {t("profile.company_edit.cancel")}
                </Button>
                <Button
                  type="submit"
                  loading={isUpdatingCompany}
                  disabled={disableCompanySave}
                >
                  {t("profile.company_edit.save")}
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
              {getFullName(user.first_name, user.last_name)}
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

        {user.company && (
          <>
            <Group justify="space-between" align="center">
              <Title order={3}>{t("profile.company_section_title")}</Title>
              <Button
                variant="light"
                leftSection={<IconSettings size={16} />}
                onClick={openCompanySettings}
              >
                {t("profile.company_edit.button")}
              </Button>
            </Group>

            <Paper withBorder p="md" radius="md">
              <Stack gap="sm">
                <Text>
                  <Text span fw={600}>
                    {t("profile.company_name")}:{" "}
                  </Text>
                  {user.company.name}
                </Text>
              </Stack>
            </Paper>
          </>
        )}
      </Stack>
    </Center>
  );
}
