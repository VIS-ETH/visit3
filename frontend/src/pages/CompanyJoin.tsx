import {
  Alert,
  Button,
  Center,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconBuilding } from "@tabler/icons-react";
import { NavLink, useLocation, useNavigate, useParams } from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAcceptCompanyInvite,
  useGetCompanyInviteInfo,
} from "../orval/generated/company/company";
import { getGetCurrentUserQueryKey } from "../orval/generated/user/user";
import { getApiErrorCode } from "../api/errors";
import CompanyJoinSignup from "../components/company/CompanyJoinSignup";
import { useCurrentUser } from "../context/useCurrentUser";

const CompanyJoin = () => {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useCurrentUser();

  const {
    data: invite,
    error: inviteError,
    isLoading,
    isError,
  } = useGetCompanyInviteInfo(token!, {
    query: { enabled: !!token, retry: false },
  });

  const {
    mutate: accept,
    error: acceptError,
    isPending,
  } = useAcceptCompanyInvite({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetCurrentUserQueryKey(),
        });
        navigate("/company", { replace: true });
      },
    },
  });

  const loginHref = `/login?next=${encodeURIComponent(location.pathname)}`;
  const invitedEmail = new URLSearchParams(location.search).get("email") ?? "";

  const inviteErrorText = (error: unknown) => {
    const code = getApiErrorCode(error);
    if (code === "error.invite_expired") return t("error.invite_expired");
    if (code === "error.invite_email_mismatch") {
      return t("company_join.email_mismatch", {
        currentEmail: user?.email ?? "",
      });
    }
    return t("error.invite_not_found");
  };

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
        <Alert
          icon={<IconAlertCircle />}
          color="red"
          title={t("company_join.invalid")}
        >
          {inviteErrorText(inviteError)}
        </Alert>
      </Center>
    );
  }

  return (
    <Center py="xl">
      <Stack align="center" gap="lg" maw={520} w="90%" px="md">
        <IconBuilding size={48} />
        <Title order={2} ta="center">
          {t("company_join.title")}
        </Title>
        <Text ta="center" c="dimmed">
          {t("company_join.joining")} <strong>{invite.company_name}</strong>
        </Text>
        {user ? (
          <Stack w="100%" gap="sm">
            {acceptError ? (
              <Alert icon={<IconAlertCircle />} color="red">
                {inviteErrorText(acceptError)}
              </Alert>
            ) : null}
            <Button
              size="lg"
              loading={isPending}
              disabled={isPending}
              onClick={() => accept({ token: token! })}
            >
              {t("company_join.button", { company: invite.company_name })}
            </Button>
          </Stack>
        ) : invite.account_exists ? (
          <Stack w="100%" gap="sm">
            <Alert icon={<IconAlertCircle />} color="blue" variant="light">
              {t("company_join.login_required")}
            </Alert>
            <Button component={NavLink} to={loginHref}>
              {t("company_join.log_in")}
            </Button>
          </Stack>
        ) : (
          <CompanyJoinSignup
            token={token!}
            invitedEmail={invitedEmail}
            loginHref={loginHref}
          />
        )}
      </Stack>
    </Center>
  );
};
export default CompanyJoin;
