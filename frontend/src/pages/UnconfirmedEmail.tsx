import { Button, Center, Stack, Title } from "@mantine/core";
import { IconMail } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useSendConfirmationMail } from "../orval/generated/user/user";
import IconTitle from "../components/IconTitle";
import { useCurrentUser } from "../context/useCurrentUser";

export default function UnconfirmedEmail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useCurrentUser();
  const [emailSent, setEmailSent] = useState(false);

  useEffect(() => {
    if (user?.email_confirmed) navigate("/", { replace: true });
  }, [user?.email_confirmed, navigate]);

  const {
    mutate: send,
    isPending,
    isError,
  } = useSendConfirmationMail({
    mutation: {
      onSuccess: () => {
        setEmailSent(true);
      },
    },
  });

  return (
    <Center>
      {!emailSent ? (
        <Stack align="center" gap="lg">
          <IconTitle
            icon={<IconMail size={50} />}
            title={t("email.confirm.unconfirmed")}
            color="blue"
          />
          {isError && <Title c="red">{t("email.confirm.error")}</Title>}
          <Button
            size="lg"
            disabled={isPending || isError}
            onClick={() => {
              send();
            }}
          >
            {t("email.confirm.button")}
          </Button>
        </Stack>
      ) : (
        <Stack align="center" gap="lg">
          <IconTitle
            icon={<IconMail size={50} />}
            title={t("email.confirm.sent")}
            color="green"
          />
        </Stack>
      )}
    </Center>
  );
}
