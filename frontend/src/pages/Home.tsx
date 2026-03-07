import { Card, Image, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import { useCurrentUser } from "../context/useCurrentUser";

export default function Home() {
  const { user } = useCurrentUser();

  return (
    <Stack gap="md">
      <Title order={3}>Welcome {user?.first_name}</Title>
      <Card
        component={Link}
        to="/kp"
        withBorder
        shadow="sm"
        padding="lg"
        radius="md"
      >
        <Card.Section>
          <Image
            src="https://placehold.co/1200x600?text=Kontaktparty"
            alt="Kontaktparty event placeholder"
            height={180}
          />
        </Card.Section>
        <Stack gap={4} mt="md">
          <Title order={4}>Kontaktparty</Title>
          <Text size="sm" c="dimmed">
            ETH job messe organized by VIS.
          </Text>
        </Stack>
      </Card>
    </Stack>
  );
}
