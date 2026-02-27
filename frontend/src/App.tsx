import { createTheme, MantineProvider, Center, Loader } from "@mantine/core";
import { generateColors } from "@mantine/colors-generator";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import { Notifications } from "@mantine/notifications";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import UserManagement from "./pages/UserManagement";
import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useNavigate,
  useLocation,
} from "react-router";
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
import { getToken } from "./api/utils";
import { useEffect } from "react";
import { UserProvider } from "./context/UserContext";
import { useCurrentUser } from "./context/useCurrentUser";
import { useGetCurrentUser } from "./orval/generated/user/user";

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
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/unconfirmed-email" element={<UnconfirmedEmail />} />
        <Route path="/confirm-email/:token" element={<ConfirmEmail />} />
        <Route path="/unconfirmed-user" element={<UnconfirmedUser />} />
        <Route element={<StaffRoute />}>
          <Route path="/user-management" element={<UserManagement />} />
          <Route path="/company-management" element={<CompanyManagement />} />
        </Route>
      </Route>
    </Routes>
  );
}

function AppWithAuth() {
  const navigate = useNavigate();
  const location = useLocation();
  const hasToken = !!getToken();

  const { data: user, isLoading } = useGetCurrentUser({
    query: {
      enabled: hasToken,
    },
  });

  useEffect(() => {
    if (!hasToken || isLoading) return;

    const isConfirmationPage =
      location.pathname === "/unconfirmed-email" ||
      location.pathname === "/unconfirmed-user" ||
      location.pathname.startsWith("/confirm-email/");

    const isPublicPage =
      location.pathname === "/login" ||
      location.pathname === "/register" ||
      location.pathname === "/forget-password" ||
      location.pathname.startsWith("/reset/") ||
      location.pathname === "/not-allowed";

    if (isConfirmationPage || isPublicPage) return;

    if (user && !user.email_confirmed) {
      navigate("/unconfirmed-email", { replace: true });
    } else if (user && !user.user_confirmed) {
      navigate("/unconfirmed-user", { replace: true });
    }
  }, [user, isLoading, hasToken, navigate, location.pathname]);

  if (hasToken && isLoading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  return (
    <UserProvider user={user} isLoading={isLoading}>
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
