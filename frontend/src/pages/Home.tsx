import { Stack, Title } from "@mantine/core";
import { useCurrentUser } from "../context/useCurrentUser";

export default function Home() {
  const { user } = useCurrentUser();

  return (
    <Stack>
      <Title order={3}>Welcome {user?.first_name}</Title>
    </Stack>
  );
}
