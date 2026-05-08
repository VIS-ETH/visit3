import { Box, Paper, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import BackButton from "./BackButton";

interface AuthCardLayoutProps {
  title: string;
  subtitle?: string;
  maxWidth?: number;
  backTo?: string;
  children: ReactNode;
  footer?: ReactNode;
}

const AuthCardLayout = ({
  title,
  subtitle,
  maxWidth = 440,
  backTo,
  children,
  footer,
}: AuthCardLayoutProps) => {
  return (
    <Box className="auth-shell">
      <Stack align="center" gap="lg" w="100%" maw={maxWidth} px="md">
        {backTo ? <BackButton to={backTo} /> : null}

        <Paper className="auth-card" w="100%" p="xl" radius="lg">
          <Stack gap="lg">
            <Stack gap={4} align="center">
              <Title className="section-title" ta="center" order={1}>
                {title}
              </Title>
              {subtitle ? (
                <Text ta="center" c="dimmed" size="sm">
                  {subtitle}
                </Text>
              ) : null}
            </Stack>
            {children}
          </Stack>
        </Paper>

        {footer ? <Box w="100%">{footer}</Box> : null}
      </Stack>
    </Box>
  );
};
export default AuthCardLayout;
