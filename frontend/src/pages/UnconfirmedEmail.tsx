import { Button, Center, Stack, Title, ThemeIcon } from "@mantine/core";
import { IconMail } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSendConfirmationMail } from "../orval/generated/user/user";

export default function UnconfirmedEmail() {
  const { t } = useTranslation();
  const [emailSent, setEmailSent] = useState(false);

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
          <ThemeIcon size={80} radius="xl" variant="light" color="blue">
            <IconMail size={50} />
          </ThemeIcon>
          <Title ta="center">{t("email.confirm.unconfirmed")}</Title>
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
          <ThemeIcon size={80} radius="xl" variant="light" color="green">
            <IconMail size={50} />
          </ThemeIcon>
          <Title ta="center">{t("email.confirm.sent")}</Title>
        </Stack>
      )}
    </Center>
  );
}
