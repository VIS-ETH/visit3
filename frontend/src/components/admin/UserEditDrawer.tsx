import {
  Button,
  Drawer,
  Group,
  SimpleGrid,
  Stack,
  Switch,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getListUsersQueryKey,
  useUpdateCompanyUser,
} from "../../orval/generated/user/user";
import { useTranslatedForm } from "../../utils/translator";
import CompanySelect from "./CompanySelect";
import {
  adminUserSchema,
  emptyAdminUserFormValues,
  toAdminUserFormValues,
  toAdminUserRequest,
} from "./user-edit-form";

interface UserEditDrawerProps {
  user: UserResponse | null;
  onClose: () => void;
  canEditPrivileges: boolean;
}

const UserEditDrawer = ({
  user,
  onClose,
  canEditPrivileges,
}: UserEditDrawerProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const form = useTranslatedForm<typeof adminUserSchema>(adminUserSchema, {
    initialValues: emptyAdminUserFormValues,
  });

  const { setValues, resetDirty, clearErrors } = form;

  useEffect(() => {
    if (!user) return;
    const values = toAdminUserFormValues(user);
    setValues(values);
    resetDirty(values);
    clearErrors();
  }, [user, setValues, resetDirty, clearErrors]);

  const { mutate: save, isPending: isSaving } = useUpdateCompanyUser({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getListUsersQueryKey(),
        });
        notifications.show({
          color: "green",
          message: t("user_management.edit.saved"),
        });
        onClose();
      },
    },
  });

  return (
    <Drawer
      onClose={onClose}
      opened={user !== null}
      position="right"
      title={t("user_management.edit.title")}
    >
      <form
        onSubmit={form.onSubmit((values) => {
          if (!user) return;
          save({
            userId: user.id,
            data: toAdminUserRequest(values, canEditPrivileges),
          });
        })}
      >
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              disabled={isSaving}
              label={t("user_management.edit.first_name")}
              {...form.getInputProps("first_name")}
            />
            <TextInput
              disabled={isSaving}
              label={t("user_management.edit.last_name")}
              {...form.getInputProps("last_name")}
            />
          </SimpleGrid>
          <TextInput
            disabled={isSaving}
            label={t("user_management.edit.email")}
            {...form.getInputProps("email")}
          />
          <TextInput
            disabled={isSaving}
            label={t("user_management.edit.phone")}
            {...form.getInputProps("phone_number")}
          />
          <CompanySelect
            disabled={isSaving}
            onChange={(value) => form.setFieldValue("company_id", value ?? "")}
            selectedOption={
              user?.company
                ? { value: user.company.id, label: user.company.name }
                : null
            }
            value={form.values.company_id || null}
          />
          <Switch
            disabled={isSaving}
            label={t("user_management.edit.user_confirmed")}
            {...form.getInputProps("user_confirmed", { type: "checkbox" })}
          />
          {canEditPrivileges ? (
            <>
              <Switch
                disabled={isSaving}
                label={t("user_management.edit.is_staff")}
                {...form.getInputProps("is_staff", { type: "checkbox" })}
              />
              <Switch
                disabled={isSaving}
                label={t("user_management.edit.is_admin")}
                {...form.getInputProps("is_admin", { type: "checkbox" })}
              />
            </>
          ) : null}
          <Group justify="flex-end">
            <Button disabled={isSaving} onClick={onClose} variant="default">
              {t("common.cancel")}
            </Button>
            <Button loading={isSaving} type="submit">
              {t("user_management.edit.save")}
            </Button>
          </Group>
        </Stack>
      </form>
    </Drawer>
  );
};

export default UserEditDrawer;
