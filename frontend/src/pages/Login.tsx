import { useState } from "react";
import {
  Alert,
  Button,
  TextInput,
  PasswordInput,
  Stack,
  Center,
} from "@mantine/core";
import type { AxiosError } from "axios";
import { NavLink, useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { useLoginUser } from "../orval/generated/users/users";

const Login = () => {
  useDocumentTitle("Login");
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");

  const { mutate: login, isPending } = useLoginUser({
    mutation: {
      onSuccess: () => {
        navigate("/");
      },
      onError: (e: AxiosError<{ detail?: any }>) => {
        const message = e.response?.data?.detail
          ? JSON.stringify(e.response.data.detail)
          : "Invalid email or password";

        setError(message);
      },
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        login({ data: { username: email, password: password } });
      }}
    >
      <Stack>
        {error && (
          <Alert color="red" title="Login Failed">
            {error}
          </Alert>
        )}

        <TextInput
          label="Email"
          placeholder="your@email.com"
          value={email}
          onChange={(e) => setEmail(e.currentTarget.value)}
          required
        />

        <PasswordInput
          label="Password"
          placeholder="***********"
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
          required
        />

        <Button
          type="submit"
          loading={isPending}
          disabled={!password || !email}
        >
          Log in
        </Button>
        <Button component={NavLink} to="/register">
          Register
        </Button>
      </Stack>
    </form>
  );
};

export default Login;
