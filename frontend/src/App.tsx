import { createTheme, MantineProvider, Text } from "@mantine/core";
import { generateColors } from "@mantine/colors-generator";
import { Route, Routes } from "react-router";
import RootLayout from "./pages/root";
import "@mantine/core/styles.css";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { configOptions } from "./utils/constants";
import Home from "./pages/Home";

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
        <Route element={<RootLayout />}>
          <Route index path="/" element={<Home />} />
          <Route path="~">
            <Route path="./" element={<Home />} />
          </Route>
        </Route>
        <Route
          path="/*"
          element={<Text>Unauthenticated... redirect to file?</Text>}
        />
      </Routes>
    </MantineProvider>
  );
}

export default App;
