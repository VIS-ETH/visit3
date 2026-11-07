import { MantineProvider, Button, Center, Group, Stack } from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Notifications } from "@mantine/notifications";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useQueryClient } from "@tanstack/react-query";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import UserManagement from "./pages/UserManagement";
import MailCampaigns from "./pages/MailCampaigns";
import MailTemplates from "./pages/MailTemplates";
import Industries from "./pages/admin/Industries";
import BookingsOverview from "./pages/BookingsOverview";
import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router";
import RootLayout from "./pages/root";
import AuthLink from "./pages/AuthLink";
import Login from "./pages/Login";
import Register from "./pages/Register";
import RequestPasswordReset from "./pages/RequestPasswordReset";
import ResetPassword from "./pages/ResetPassword";
import UnconfirmedEmail from "./pages/UnconfirmedEmail";
import ConfirmEmail from "./pages/ConfirmEmail";
import PendingActivation from "./pages/PendingActivation";
import CompanyManagement from "./pages/CompanyManagement";
import CompanyProfile from "./pages/CompanyProfile";
import CompanyProfileAdmin from "./pages/admin/CompanyProfileAdmin";
import CompanyProfileEdit from "./pages/company/CompanyProfileEdit";
import CompanyJoin from "./pages/CompanyJoin";
import SetupCompany from "./pages/SetupCompany";
import Profile from "./pages/Profile";
import NotAllowed from "./pages/NotAllowed";
import NotFound from "./pages/NotFound";
import KpJoin from "./pages/KpJoin";
import KpBooking from "./pages/KpBooking";
import KpBookingConfirmation from "./pages/KpBookingConfirmation";
import KpBookingManage from "./pages/KpBookingManage";
import KpBookingManageOverview from "./pages/KpBookingManageOverview";
import KpBookingDetails from "./pages/KpBookingDetails";
import KpServiceForm from "./pages/KpServiceForm";
import Kp from "./pages/Kp";
import { UserProvider } from "./context/UserContext";
import { useCurrentUser } from "./context/useCurrentUser";
import {
  getGetCurrentUserQueryKey,
  useGetCurrentUser,
} from "./orval/generated/user/user";
import {
  getToken,
  getTokenSubject,
  isImpersonating,
  isLoggedOut,
  refreshToken,
  subscribeToTokenStorage,
} from "./api/utils";
import { getApiErrorStatus } from "./api/errors";
import { loginPathWithNext, takeLoginNext } from "./utils/navigation";
import { stopImpersonating } from "./components/admin/useImpersonate";
import PageLoader from "./components/PageLoader";
import ErrorAlert from "./components/ErrorAlert";
import makeVisitTheme, {
  visitCssVariablesResolver,
} from "./theme/makeVisitTheme";
import { colorSchemeManager } from "./theme/color-scheme-manager";

const primaryColor = configOptions().primaryColor;
const theme = makeVisitTheme(primaryColor);

function LoginRedirect() {
  const { pathname, search, hash } = useLocation();
  return (
    <Navigate to={loginPathWithNext(`${pathname}${search}${hash}`)} replace />
  );
}

function PendingLoginRedirect() {
  const { user } = useCurrentUser();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) return;
    const next = takeLoginNext();
    if (next) navigate(next, { replace: true });
  }, [user, navigate]);

  return null;
}

function StaffRoute() {
  const { user } = useCurrentUser();
  if (!user) return <LoginRedirect />;
  return user.is_staff || user.is_admin ? (
    <Outlet />
  ) : (
    <Navigate to="/not-allowed" replace />
  );
}

function PresidentRoute() {
  const { user } = useCurrentUser();
  if (!user) return <LoginRedirect />;
  return user.is_kp_president ? (
    <Outlet />
  ) : (
    <Navigate to="/not-allowed" replace />
  );
}

function CompanyRoute() {
  const { user } = useCurrentUser();
  if (!user) return <LoginRedirect />;
  return user.company_id ? <Outlet /> : <Navigate to="/not-allowed" replace />;
}

function ActivatedRoute() {
  const { user } = useCurrentUser();
  if (user && !user.is_staff && !user.is_admin && !user.is_company)
    return <PendingActivation />;
  return <Outlet />;
}

function ConfirmedRoute() {
  const { user } = useCurrentUser();
  if (!user) return <LoginRedirect />;
  if (!user.email_confirmed)
    return <Navigate to="/unconfirmed-email" replace />;
  if (user.is_company && !user.company_id)
    return <Navigate to="/setup-company" replace />;
  return <Outlet />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<RootLayout navbarHidden={true} />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/reset-password" element={<RequestPasswordReset />} />
        <Route path="/reset/:token" element={<ResetPassword />} />
        <Route path="/auth/link/:token" element={<AuthLink />} />
        <Route path="/not-allowed" element={<NotAllowed />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route element={<RootLayout navbarHidden={false} />}>
        <Route path="/setup-company" element={<SetupCompany />} />
        <Route path="/company/join/:token" element={<CompanyJoin />} />
        <Route path="/unconfirmed-email" element={<UnconfirmedEmail />} />
        <Route path="/confirm-email/:token" element={<ConfirmEmail />} />
        <Route element={<ActivatedRoute />}>
          <Route element={<ConfirmedRoute />}>
            <Route index path="/" element={<Home />} />
            <Route path="/kp" element={<Kp />} />
            <Route path="/kp/:id" element={<Kp />} />
            <Route path="/kp/:id/booking" element={<KpBooking />} />
            <Route
              path="/kp/:id/booking/:bookingId"
              element={<KpBookingConfirmation />}
            />
            <Route
              path="/kp/:id/booking/:bookingId/manage"
              element={<KpBookingManageOverview />}
            />
            <Route
              path="/kp/:id/booking/:bookingId/manage/services"
              element={<KpBookingManage />}
            />
          </Route>
          <Route element={<CompanyRoute />}>
            <Route path="/profile" element={<Profile />} />
            <Route path="/company" element={<CompanyProfile />} />
            <Route path="/company/profile" element={<CompanyProfileEdit />} />
            <Route path="/kp/join" element={<KpJoin />} />
          </Route>
          <Route element={<StaffRoute />}>
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/admin/mail-templates" element={<MailTemplates />} />
            <Route path="/admin/industries" element={<Industries />} />
            <Route path="/bookings-overview" element={<BookingsOverview />} />
            <Route path="/company-management" element={<CompanyManagement />} />
            <Route
              path="/company-management/:companyId/profile"
              element={<CompanyProfileAdmin />}
            />
            <Route
              path="/kp/:id/bookings/:bookingId"
              element={<KpBookingDetails />}
            />
          </Route>
          <Route element={<PresidentRoute />}>
            <Route path="/admin/mail-campaigns" element={<MailCampaigns />} />
            <Route path="/kp/:id/services/new" element={<KpServiceForm />} />
            <Route
              path="/kp/:id/services/:serviceId"
              element={<KpServiceForm />}
            />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}

function SessionLoadError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <Center h="100%" w="100%" py="xl">
      <Stack align="center" gap="md" maw={520} px="md">
        <ErrorAlert>{t("error.session_load_failed")}</ErrorAlert>
        <Group justify="center">
          <Button onClick={onRetry}>{t("error.retry")}</Button>
          {isImpersonating() ? (
            <Button variant="light" onClick={stopImpersonating}>
              {t("impersonation.stop")}
            </Button>
          ) : null}
        </Group>
      </Stack>
    </Center>
  );
}

function AppWithAuth() {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState<boolean>(() => !!getToken());
  const [isFetchingAccessToken, setIsFetchingAccessToken] =
    useState<boolean>(!getToken());
  const subjectRef = useRef(getTokenSubject());

  useEffect(() => {
    const onTokenChanged = () => {
      subjectRef.current = getTokenSubject();
      setHasToken(!!getToken());
    };

    const unsubscribeFromOtherTabs = subscribeToTokenStorage(() => {
      const subject = getTokenSubject();
      if (subject === subjectRef.current) {
        void queryClient.invalidateQueries({
          queryKey: getGetCurrentUserQueryKey(),
        });
      } else if (subject) {
        void queryClient.resetQueries();
      } else {
        queryClient.clear();
      }
      onTokenChanged();
    });

    window.addEventListener("auth-token-changed", onTokenChanged);
    return () => {
      window.removeEventListener("auth-token-changed", onTokenChanged);
      unsubscribeFromOtherTabs();
    };
  }, [queryClient]);

  useEffect(() => {
    if (hasToken || isLoggedOut()) {
      setIsFetchingAccessToken(false);
      return;
    }

    let isMounted = true;
    setIsFetchingAccessToken(true);

    refreshToken().finally(() => {
      if (!isMounted) return;
      setHasToken(!!getToken());
      setIsFetchingAccessToken(false);
    });

    return () => {
      isMounted = false;
    };
  }, [hasToken]);

  const {
    data: user,
    error,
    isError,
    isLoading,
    refetch,
  } = useGetCurrentUser({
    query: {
      enabled: hasToken,
      retry: false,
    },
  });

  const contextUser = hasToken ? user : undefined;

  if (isFetchingAccessToken || (hasToken && isLoading)) {
    return <PageLoader />;
  }

  if (hasToken && isError && getApiErrorStatus(error) !== 401) {
    return (
      <SessionLoadError
        onRetry={() => {
          void refetch();
        }}
      />
    );
  }

  return (
    <UserProvider user={contextUser} isLoading={isLoading}>
      <PendingLoginRedirect />
      <AppRoutes />
    </UserProvider>
  );
}

function App() {
  return (
    <MantineProvider
      theme={theme}
      colorSchemeManager={colorSchemeManager}
      cssVariablesResolver={visitCssVariablesResolver}
      defaultColorScheme="auto"
    >
      <Notifications
        position="top-center"
        limit={1}
        zIndex={1000}
        autoClose={5000}
      />
      <ReactQueryDevtools />
      <AppWithAuth />
    </MantineProvider>
  );
}

export default App;
