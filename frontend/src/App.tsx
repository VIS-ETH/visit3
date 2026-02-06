import { createTheme, MantineProvider } from "@mantine/core";
import { generateColors } from "@mantine/colors-generator";
import "@mantine/core/styles.css";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";
import { Route, Routes } from "react-router";
import RootLayout from "./pages/root";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgetPassword from "./pages/ForgetPassword";
import ResetPassword from "./pages/ResetPassword";

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
          <Route path="~">
            <Route path="./" element={<Home />} />
          </Route>
        </Route>
      </Routes>
    </MantineProvider>
  );
}

export default App;
