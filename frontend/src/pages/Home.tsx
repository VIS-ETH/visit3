import { Button, Stack, Title } from "@mantine/core";
import {
  useLoginUser,
  useLogoutUser,
  useReadUsersMe,
  useRegisterUser,
} from "../orval/generated/default/default";
import { redirect } from "react-router";

export default function Home() {
  const { mutate: register } = useRegisterUser();
  const { data: userMe, refetch: fetchUser } = useReadUsersMe({
    query: { enabled: false },
  });
  const { mutate: login } = useLoginUser();
  const { mutate: logout } = useLogoutUser({
    mutation: {
      onSuccess: () => {
        sessionStorage.removeItem("token");
        window.location.href = "/login";
      },
    },
  });

  return (
    <Stack>
      <Title order={3}>Welcome {}</Title>
      <Title order={2}>File hierarchy</Title>

      {userMe?.email}
      <Button
        onClick={() => {
          fetchUser();
        }}
      >
        User
      </Button>
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
      <Button
        onClick={() => {
          logout();
        }}
      >
        Logout
      </Button>
    </Stack>
  );
}
