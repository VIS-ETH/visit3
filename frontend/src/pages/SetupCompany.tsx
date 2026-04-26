import {
  Alert,
  Button,
  Center,
  Divider,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconBuilding, IconInfoCircle, IconMail } from "@tabler/icons-react";
import { useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useSetupCompany } from "../orval/generated/company/company";
import { getGetCurrentUserQueryKey } from "../orval/generated/user/user";
import { useCurrentUser } from "../context/useCurrentUser";
import { useTranslatedForm } from "../utils/translator";
import { setupCompanySchema } from "../schemas/setupCompanySchema";
import { getSafeNextPath } from "../utils/navigation";

export default function SetupCompany() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();
  const nextPath = getSafeNextPath(location.search);

  useEffect(() => {
    if (user?.company_id) navigate("/company", { replace: true });
  }, [user?.company_id, navigate]);

  const form = useTranslatedForm<typeof setupCompanySchema>(
    setupCompanySchema,
    {
      initialValues: { name: "" },
      validateInputOnChange: true,
    },
  );

  const { mutate: setup, isPending } = useSetupCompany({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetCurrentUserQueryKey(),
        });
        navigate("/company", { replace: true });
      },
    },
  });

  if (!user) {
    return (
      <Center py="xl">
        <Stack w="100%" maw={560} gap="lg" px="md" align="center">
          <Title order={2}>{t("setup_company.login_required")}</Title>
          <Text ta="center" c="dimmed">
            {t("setup_company.login_required_description")}
          </Text>
          <Button
            component={NavLink}
            to={
              nextPath
                ? `/login?next=${encodeURIComponent(nextPath)}`
                : "/login?next=%2Fsetup-company"
            }
          >
            {t("email.confirm.go_to_login")}
          </Button>
        </Stack>
      </Center>
    );
  }

  return (
    <Center py="xl">
      <Stack w="100%" maw={560} gap="xl" px="md">
        <Title order={2}>{t("setup_company.title")}</Title>

        <Paper withBorder p="xl" radius="md">
          <Stack gap="md">
            <Stack gap={4}>
              <Title order={4}>
                <IconBuilding
                  size={18}
                  style={{ marginRight: 6, verticalAlign: "middle" }}
                />
                {t("setup_company.create_title")}
              </Title>
              <Text size="sm" c="dimmed">
                {t("setup_company.create_description")}
              </Text>
            </Stack>
            <form
              onSubmit={form.onSubmit((v) => setup({ data: { name: v.name } }))}
            >
              <Stack gap="md">
                <TextInput
                  label={t("setup_company.name_label")}
                  placeholder={t("setup_company.name_placeholder")}
                  {...form.getInputProps("name")}
                />
                <Button
                  type="submit"
                  loading={isPending}
                  disabled={isPending || !form.isValid()}
                >
                  {t("setup_company.create_button")}
                </Button>
              </Stack>
            </form>
          </Stack>
        </Paper>

        <Divider label={t("setup_company.or")} labelPosition="center" />

        <Paper withBorder p="xl" radius="md">
          <Stack gap="md">
            <Stack gap={4}>
              <Title order={4}>
                <IconMail
                  size={18}
                  style={{ marginRight: 6, verticalAlign: "middle" }}
                />
                {t("setup_company.invite_title")}
              </Title>
              <Text size="sm" c="dimmed">
                {t("setup_company.invite_description")}
              </Text>
            </Stack>
            <Alert
              icon={<IconInfoCircle size={16} />}
              color="blue"
              variant="light"
            >
              {t("setup_company.invite_hint", { email: user.email })}
            </Alert>
          </Stack>
        </Paper>
      </Stack>
    </Center>
  );
}
