import { createTheme, MantineProvider } from "@mantine/core";
import { generateColors } from "@mantine/colors-generator";
import "@mantine/core/styles.css";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import UserManagement from "./pages/UserManagement";
import { Route, Routes } from "react-router";
import RootLayout from "./pages/root";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgetPassword from "./pages/ForgetPassword";
import ResetPassword from "./pages/ResetPassword";
import UnconfirmedEmail from "./pages/UnconfirmedEmail";
import ConfirmEmail from "./pages/ConfirmEmail";
import UnconfirmedUser from "./pages/UnconfirmedUser";

const primaryColor = configOptions().primaryColor;
const theme = createTheme({
  primaryColor: "brand",
  colors: {
    brand: generateColors(primaryColor),
  },
  autoContrast: true,
});

function App() {
  return (
    <MantineProvider theme={theme}>
      <ReactQueryDevtools />
      <Routes>
        <Route element={<RootLayout navbarHidden={true} />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forget_password" element={<ForgetPassword />} />
          <Route path="/reset/:token" element={<ResetPassword />} />
        </Route>
        <Route element={<RootLayout navbarHidden={false} />}>
          <Route index path="/" element={<Home />} />
          <Route path="/unconfirmed_email" element={<UnconfirmedEmail />} />
          <Route path="/confirm_email/:token" element={<ConfirmEmail />} />
          <Route path="/unconfirmed_user" element={<UnconfirmedUser />} />
          <Route path="/user-management" element={<UserManagement />} />
        </Route>
      </Routes>
    </MantineProvider>
  );
}

export default App;
