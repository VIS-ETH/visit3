import { Stack, Title } from "@mantine/core";
import { useReadUsersMe } from "../orval/generated/users/users";

export default function Home() {
  const { data: userMe} = useReadUsersMe({
  });

  return (
    <Stack>
      <Title order={3}>Welcome {userMe?.email}</Title>
    </Stack>
  );
}
