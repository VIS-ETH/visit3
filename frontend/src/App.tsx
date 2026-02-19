import { createTheme, MantineProvider } from "@mantine/core";
import { generateColors } from "@mantine/colors-generator";
import "@mantine/core/styles.css";
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
import NotAllowed from "./pages/NotAllowed";
import NotFound from "./pages/NotFound";
import { isStaff } from "./api/utils";

const primaryColor = configOptions().primaryColor;
const theme = createTheme({
  primaryColor: "brand",
  colors: {
    brand: generateColors(primaryColor),
  },
  autoContrast: true,
});

function StaffRoute() {
  return isStaff() ? <Outlet /> : <Navigate to="/not-allowed" replace />;
}

function App() {
  return (
    <MantineProvider theme={theme}>
      <ReactQueryDevtools />
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
          <Route index path="/" element={<Home />} />
          <Route path="/unconfirmed-email" element={<UnconfirmedEmail />} />
          <Route path="/confirm-email/:token" element={<ConfirmEmail />} />
          <Route path="/unconfirmed-user" element={<UnconfirmedUser />} />
          <Route element={<StaffRoute />}>
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/company-management" element={<CompanyManagement />} />
          </Route>
        </Route>
      </Routes>
    </MantineProvider>
  );
}

export default App;
