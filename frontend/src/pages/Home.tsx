import { Button, Stack, Title } from "@mantine/core";
import {
  useLoginUser,
  useReadUsersMe,
  useRegisterUser,
} from "../orval/generated/default/default";

export default function Home() {
  const { mutate: register } = useRegisterUser();
  const { data: userMe } = useReadUsersMe({
    query: {
      refetchInterval: 5000,
    },
  });
  const { mutate: login } = useLoginUser();

  return (
    <Stack>
      <Title order={3}>Welcome {}</Title>
      <Title order={2}>File hierarchy</Title>

      {userMe?.email}
      <Button
        onClick={() => {
          register({
            data: {
              email: String(0),
              password: "aaaaaaaaaaaaaa",
            },
          });
        }}
      >
        Register
      </Button>
      <Button
        onClick={() => {
          login({
            data: {
              username: String(0),
              password: "aaaaaaaaaaaaaa",
            },
          });
        }}
      >
        Login
      </Button>
    </Stack>
  );
}
