import { Paper, Stack, Title } from "@mantine/core";
import type { ReactNode } from "react";

interface CompanyProfileSectionProps {
  title: string;
  children: ReactNode;
}

const CompanyProfileSection = ({
  title,
  children,
}: CompanyProfileSectionProps) => (
  <Paper withBorder p="lg" radius="md">
    <Stack gap="md">
      <Title order={4}>{title}</Title>
      {children}
    </Stack>
  </Paper>
);

export default CompanyProfileSection;
