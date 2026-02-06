import { Stack, Title } from "@mantine/core";
import { useReadUsersMe } from "../orval/generated/users/users";
import { isCompany } from "../api/auth";

export default function Home() {
  const { data: userMe} = useReadUsersMe({
  });

  return (
    <Stack>
      <Title order={3}>Welcome {isCompany() ? "Company" : "Admin"} {userMe?.email}</Title>
    </Stack>
  );
}
