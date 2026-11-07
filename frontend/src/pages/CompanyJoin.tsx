import { Alert, Button, Center, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle, IconBuilding } from "@tabler/icons-react";
import {
  Navigate,
  NavLink,
  useLocation,
  useNavigate,
  useParams,
} from "react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAcceptCompanyInvite,
  useGetCompanyInviteInfo,
} from "../orval/generated/company/company";
import { getGetCurrentUserQueryKey } from "../orval/generated/user/user";
import { getApiErrorCode, getApiErrorStatus } from "../api/errors";
import CompanyJoinSignup from "../components/company/CompanyJoinSignup";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import { useCurrentUser } from "../context/useCurrentUser";

const HANDLED_STATUSES = [400, 403, 404] as const;

const isHandledStatus = (error: unknown) => {
  const status = getApiErrorStatus(error);
  return status !== undefined && HANDLED_STATUSES.some((s) => s === status);
};

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
    request: { quietStatuses: HANDLED_STATUSES },
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
    request: { quietStatuses: HANDLED_STATUSES },
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
    if (code === "error.invite_not_found") return t("error.invite_not_found");
    if (code === "error.not_allowed" && user?.company_id) {
      return t("company_join.already_in_company");
    }
    return t("server.error");
  };

  if (isLoading) {
    return <PageLoader />;
  }

  if (
    isError &&
    user?.company_id &&
    getApiErrorCode(inviteError) === "error.invite_not_found"
  ) {
    return <Navigate to="/company" replace />;
  }

  if (isError && !isHandledStatus(inviteError)) {
    return (
      <Center py="xl">
        <ErrorAlert />
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
          {t("company_join.joining", { company: invite.company_name })}
        </Text>
        {user ? (
          <Stack w="100%" gap="sm">
            {acceptError ? (
              <ErrorAlert>
                {isHandledStatus(acceptError)
                  ? inviteErrorText(acceptError)
                  : t("server.error")}
              </ErrorAlert>
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
