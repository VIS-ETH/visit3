import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconMail, IconSettings } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import {
  useCreateCompanyInvite,
  useGetMyCompanyMembers,
  useUpdateMyCompany,
} from "../orval/generated/company/company";
import {
  getGetUserProfileQueryKey,
  useGetUserProfile,
} from "../orval/generated/user/user";
import { useTranslatedForm } from "../utils/translator";
import { companySchema } from "../schemas/companySchema";

const inviteSchema = z.object({
  email: z.string().trim().min(1, "register.required").email("email.valid"),
});

export default function CompanyProfile() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [settingsOpened, setSettingsOpened] = useState(false);

  const { data: userProfile } = useGetUserProfile();
  const {
    data: members = [],
    isLoading: membersLoading,
    isError: membersError,
  } = useGetMyCompanyMembers();

  const companyForm = useTranslatedForm<typeof companySchema>(companySchema, {
    initialValues: { name: "" },
    validateInputOnChange: true,
  });

  const inviteForm = useTranslatedForm<typeof inviteSchema>(inviteSchema, {
    initialValues: { email: "" },
    validateInputOnChange: true,
  });

  const { mutate: updateCompany, isPending: isUpdating } = useUpdateMyCompany({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetUserProfileQueryKey(),
        });
        setSettingsOpened(false);
        notifications.show({
          color: "green",
          title: t("company_profile.settings_success"),
          message: "",
        });
      },
    },
  });

  const { mutate: sendInvite, isPending: isSending } = useCreateCompanyInvite({
    mutation: {
      onSuccess: () => {
        const email = inviteForm.values.email;
        inviteForm.reset();
        notifications.show({
          color: "green",
          title: t("company_profile.invite_success"),
          message: email,
        });
      },
    },
  });

  const openSettings = () => {
    const name = userProfile?.company?.name ?? "";
    companyForm.setInitialValues({ name });
    companyForm.setValues({ name });
    companyForm.clearErrors();
    setSettingsOpened(true);
  };

  return (
    <Center h="100%" w="100%" py="xl">
      <Stack w="100%" maw={700} gap="lg">
        <Group justify="space-between" align="center">
          <Title order={2}>
            {userProfile?.company?.name ?? t("company_profile.title")}
          </Title>
          <Button
            variant="light"
            leftSection={<IconSettings size={16} />}
            onClick={openSettings}
          >
            {t("company_profile.settings_button")}
          </Button>
        </Group>

        <Modal
          opened={settingsOpened}
          onClose={() => {
            if (!isUpdating) setSettingsOpened(false);
          }}
          title={t("company_profile.settings_title")}
          centered
          closeOnEscape={!isUpdating}
          closeOnClickOutside={!isUpdating}
          withCloseButton={!isUpdating}
        >
          <form
            onSubmit={companyForm.onSubmit((v) =>
              updateCompany({ data: { name: v.name } }),
            )}
          >
            <Stack gap="md">
              <TextInput
                label={t("company_profile.name_label")}
                placeholder={t("company_profile.name_placeholder")}
                {...companyForm.getInputProps("name")}
                disabled={isUpdating}
              />
              <Group justify="flex-end">
                <Button
                  variant="default"
                  onClick={() => setSettingsOpened(false)}
                  disabled={isUpdating}
                >
                  {t("company_profile.cancel")}
                </Button>
                <Button
                  type="submit"
                  loading={isUpdating}
                  disabled={isUpdating || !companyForm.isValid()}
                >
                  {t("company_profile.save")}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>

        <Paper withBorder p="xl" radius="md">
          <Stack gap="md">
            <Title order={4}>
              <IconMail
                size={18}
                style={{ marginRight: 6, verticalAlign: "middle" }}
              />
              {t("company_profile.invite_title")}
            </Title>
            <form
              onSubmit={inviteForm.onSubmit((v) =>
                sendInvite({ data: { email: v.email } }),
              )}
            >
              <Group align="flex-end" gap="sm">
                <TextInput
                  style={{ flex: 1 }}
                  label={t("company_profile.invite_email")}
                  placeholder={t("company_profile.invite_email_placeholder")}
                  {...inviteForm.getInputProps("email")}
                />
                <Button
                  type="submit"
                  loading={isSending}
                  disabled={isSending || !inviteForm.isValid()}
                >
                  {t("company_profile.invite_button")}
                </Button>
              </Group>
            </form>
          </Stack>
        </Paper>

        <Title order={3}>{t("company_profile.members_title")}</Title>

        {membersLoading ? (
          <Center>
            <Loader />
          </Center>
        ) : membersError ? (
          <Alert icon={<IconAlertCircle />} color="red">
            {t("server.error")}
          </Alert>
        ) : members.length === 0 ? (
          <Text c="dimmed">{t("company_profile.no_members")}</Text>
        ) : (
          <Paper withBorder radius="md" style={{ overflow: "hidden" }}>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("user_management.name")}</Table.Th>
                  <Table.Th>{t("user_management.email")}</Table.Th>
                  <Table.Th>{t("user_management.phone")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {members.map((m) => (
                  <Table.Tr key={m.id}>
                    <Table.Td>
                      {[m.first_name, m.last_name].filter(Boolean).join(" ") ||
                        "-"}
                    </Table.Td>
                    <Table.Td>{m.email}</Table.Td>
                    <Table.Td>{m.phone_number ?? "-"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        )}
      </Stack>
    </Center>
  );
}
