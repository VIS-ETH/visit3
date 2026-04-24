import { Button, Center, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import IconTitle from "./IconTitle";

interface StatusPageProps {
  code: string;
  title: string;
  description: string;
  icon: ReactNode;
  iconColor: string;
  homeLabel: string;
}

export default function StatusPage({
  code,
  title,
  description,
  icon,
  iconColor,
  homeLabel,
}: StatusPageProps) {
  return (
    <Center h="100%" w="100%" py="xl">
      <Stack align="center" gap="md" maw={520} px="md">
        <IconTitle
          icon={icon}
          title={code}
          color={iconColor}
          iconSize={64}
          titleOrder={1}
        />
        <Title order={3} ta="center">
          {title}
        </Title>
        <Text ta="center" c="dimmed">
          {description}
        </Text>
        <Button component="a" href="/" variant="light">
          {homeLabel}
        </Button>
      </Stack>
    </Center>
  );
}
