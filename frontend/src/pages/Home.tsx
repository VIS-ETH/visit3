import { Stack, Title } from "@mantine/core";
import { isCompany } from "../api/utils";
import { useReadUsersMe } from "../orval/generated/user/user";

export default function Home() {
  const { data: userMe } = useReadUsersMe({});

  return (
    <Stack>
      <Title order={3}>
        Welcome {isCompany() ? "Company" : "Admin"} {userMe?.email}
      </Title>
    </Stack>
  );
}
