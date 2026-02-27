import { Stack, Title } from "@mantine/core";
import { isCompany } from "../api/utils";
import { useCurrentUser } from "../context/useCurrentUser";

export default function Home() {
  const { user } = useCurrentUser();

  return (
    <Stack>
      <Title order={3}>
        Welcome {isCompany() ? "Company" : "Admin"} {user?.email}
      </Title>
    </Stack>
  );
}
