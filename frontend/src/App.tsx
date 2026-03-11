import { createTheme, MantineProvider, Center, Loader } from "@mantine/core";
import { useEffect, useState } from "react";
import { generateColors } from "@mantine/colors-generator";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import { Notifications } from "@mantine/notifications";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import UserManagement from "./pages/UserManagement";
import { Navigate, Outlet, Route, Routes } from "react-router";
import RootLayout from "./pages/root";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgetPassword from "./pages/ForgetPassword";
import ResetPassword from "./pages/ResetPassword";
import UnconfirmedEmail from "./pages/UnconfirmedEmail";
import ConfirmEmail from "./pages/ConfirmEmail";
import UnconfirmedUser from "./pages/UnconfirmedUser";
import CompanyManagement from "./pages/CompanyManagement";
import Profile from "./pages/Profile";
import NotAllowed from "./pages/NotAllowed";
import NotFound from "./pages/NotFound";
import Kp from "./pages/Kp";
import KpJoin from "./pages/KpJoin";
import KpDashboard from "./pages/KpDashboard";
import { UserProvider } from "./context/UserContext";
import { useCurrentUser } from "./context/useCurrentUser";
import { useGetCurrentUser } from "./orval/generated/user/user";
import { getToken, refreshToken } from "./api/utils";

const primaryColor = configOptions().primaryColor;
const theme = createTheme({
  primaryColor: "brand",
  colors: {
    brand: generateColors(primaryColor),
  },
  autoContrast: true,
});

function StaffRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user?.is_staff || user?.is_admin ? (
    <Outlet />
  ) : (
    <Navigate to="/not-allowed" replace />
  );
}

function CompanyRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user?.is_company ? <Outlet /> : <Navigate to="/not-allowed" replace />;
}

function ConfirmedRoute() {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  if (!user.email_confirmed) {
    return <Navigate to="/unconfirmed-email" replace />;
  }
  if (!user.user_confirmed) {
    return <Navigate to="/unconfirmed-user" replace />;
  }
  return <Outlet />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<RootLayout navbarHidden={true} />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forget-password" element={<ForgetPassword />} />
        <Route path="/reset/:token" element={<ResetPassword />} />
        <Route path="/not-allowed" element={<NotAllowed />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route element={<RootLayout navbarHidden={false} />}>
        <Route element={<ConfirmedRoute />}>
          <Route index path="/" element={<Home />} />
          <Route path="/kp" element={<Kp />} />
        </Route>
        <Route element={<CompanyRoute />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/kp/join" element={<KpJoin />} />
        </Route>
        <Route path="/unconfirmed-email" element={<UnconfirmedEmail />} />
        <Route path="/confirm-email/:token" element={<ConfirmEmail />} />
        <Route path="/unconfirmed-user" element={<UnconfirmedUser />} />
        <Route element={<StaffRoute />}>
          <Route path="/user-management" element={<UserManagement />} />
          <Route path="/company-management" element={<CompanyManagement />} />
          <Route path="/kp/dashboard" element={<KpDashboard />} />
        </Route>
      </Route>
    </Routes>
  );
}

function AppWithAuth() {
  const [hasToken, setHasToken] = useState<boolean>(() => !!getToken());
  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(!getToken());

  useEffect(() => {
    const onTokenChanged = () => {
      setHasToken(!!getToken());
    };

    window.addEventListener("auth-token-changed", onTokenChanged);
    return () => {
      window.removeEventListener("auth-token-changed", onTokenChanged);
    };
  }, []);

  // This is needed because the user has no token on first load if they are using keycloak
  // So we get them a new token before trying to load the user
  useEffect(() => {
    if (hasToken) {
      setIsBootstrapping(false);
      return;
    }

    let isMounted = true;
    setIsBootstrapping(true);

    refreshToken().finally(() => {
      if (!isMounted) return;
      setHasToken(!!getToken());
      setIsBootstrapping(false);
    });

    return () => {
      isMounted = false;
    };
  }, [hasToken]);

  const { data: user, isLoading } = useGetCurrentUser({
    query: {
      enabled: hasToken,
      retry: false,
    },
  });

  const contextUser = hasToken ? user : undefined;

  if (isBootstrapping || (hasToken && isLoading)) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  return (
    <UserProvider user={contextUser} isLoading={isBootstrapping || isLoading}>
      <AppRoutes />
    </UserProvider>
  );
}

function App() {
  return (
    <MantineProvider theme={theme}>
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
