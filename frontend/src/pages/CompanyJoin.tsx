import { Alert, Button, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle, IconBuilding } from "@tabler/icons-react";
import { useNavigate, useParams } from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAcceptCompanyInvite,
  useGetCompanyInviteInfo,
} from "../orval/generated/company/company";
import { getGetCurrentUserQueryKey } from "../orval/generated/user/user";

export default function CompanyJoin() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: invite, isLoading, isError } = useGetCompanyInviteInfo(token!, {
    query: { enabled: !!token },
  });

  const { mutate: accept, isPending } = useAcceptCompanyInvite({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: getGetCurrentUserQueryKey() });
        navigate("/company", { replace: true });
      },
    },
  });

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError || !invite) {
    return (
      <Center py="xl">
        <Alert icon={<IconAlertCircle />} color="red" title={t("company_join.invalid")}>
          {t("error.invite_not_found")}
        </Alert>
      </Center>
    );
  }

  return (
    <Center py="xl">
      <Stack align="center" gap="lg" maw={480} w="90%" px="md">
        <IconBuilding size={48} />
        <Title order={2} ta="center">{t("company_join.title")}</Title>
        <Text ta="center" c="dimmed">
          {t("company_join.joining")} <strong>{invite.company_name}</strong>
        </Text>
        <Button
          size="lg"
          loading={isPending}
          disabled={isPending}
          onClick={() => accept({ token: token! })}
        >
          {t("company_join.button", { company: invite.company_name })}
        </Button>
      </Stack>
    </Center>
  );
}
