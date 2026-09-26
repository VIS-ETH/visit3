import {
  MantineProvider,
  Alert,
  Button,
  Center,
  Loader,
  Stack,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Notifications } from "@mantine/notifications";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useQueryClient } from "@tanstack/react-query";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import UserManagement from "./pages/UserManagement";
import MailTemplates from "./pages/MailTemplates";
import Industries from "./pages/admin/Industries";
import { Navigate, Outlet, Route, Routes } from "react-router";
import RootLayout from "./pages/root";
import AuthLink from "./pages/AuthLink";
import Login from "./pages/Login";
import Register from "./pages/Register";
import RequestPasswordReset from "./pages/RequestPasswordReset";
import ResetPassword from "./pages/ResetPassword";
import UnconfirmedEmail from "./pages/UnconfirmedEmail";
import ConfirmEmail from "./pages/ConfirmEmail";
import UnconfirmedUser from "./pages/UnconfirmedUser";
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
import { getToken, refreshToken, subscribeToTokenStorage } from "./api/utils";
import { getApiErrorStatus } from "./api/errors";
import makeVisitTheme, {
  visitCssVariablesResolver,
} from "./theme/makeVisitTheme";
import { colorSchemeManager } from "./theme/color-scheme-manager";

const primaryColor = configOptions().primaryColor;
const theme = makeVisitTheme(primaryColor);

function StaffRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user.is_staff || user.is_admin ? (
    <Outlet />
  ) : (
    <Navigate to="/not-allowed" replace />
  );
}

function PresidentRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user.is_kp_president ? (
    <Outlet />
  ) : (
    <Navigate to="/not-allowed" replace />
  );
}

function CompanyRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user.company_id ? <Outlet /> : <Navigate to="/not-allowed" replace />;
}

function ConfirmedRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  if (!user.email_confirmed)
    return <Navigate to="/unconfirmed-email" replace />;
  if (!user.user_confirmed) return <Navigate to="/unconfirmed-user" replace />;
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
        <Route path="/setup-company" element={<SetupCompany />} />
        <Route path="/company/join/:token" element={<CompanyJoin />} />
        <Route path="/unconfirmed-email" element={<UnconfirmedEmail />} />
        <Route path="/confirm-email/:token" element={<ConfirmEmail />} />
        <Route path="/unconfirmed-user" element={<UnconfirmedUser />} />
        <Route element={<StaffRoute />}>
          <Route path="/user-management" element={<UserManagement />} />
          <Route path="/admin/mail-templates" element={<MailTemplates />} />
          <Route path="/admin/industries" element={<Industries />} />
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
          <Route path="/kp/:id/services/new" element={<KpServiceForm />} />
          <Route
            path="/kp/:id/services/:serviceId"
            element={<KpServiceForm />}
          />
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
        <Alert icon={<IconAlertCircle />} color="red" title={t("error.title")}>
          {t("error.session_load_failed")}
        </Alert>
        <Button onClick={onRetry}>{t("error.retry")}</Button>
      </Stack>
    </Center>
  );
}

function AppWithAuth() {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState<boolean>(() => !!getToken());
  const [isFetchingAccessToken, setIsFetchingAccessToken] =
    useState<boolean>(!getToken());

  useEffect(() => {
    const onTokenChanged = () => {
      setHasToken(!!getToken());
    };

    const unsubscribeFromOtherTabs = subscribeToTokenStorage(() => {
      queryClient.invalidateQueries({ queryKey: getGetCurrentUserQueryKey() });
      onTokenChanged();
    });

    window.addEventListener("auth-token-changed", onTokenChanged);
    return () => {
      window.removeEventListener("auth-token-changed", onTokenChanged);
      unsubscribeFromOtherTabs();
    };
  }, [queryClient]);

  useEffect(() => {
    if (hasToken) {
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
    return (
      <Center>
        <Loader />
      </Center>
    );
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
