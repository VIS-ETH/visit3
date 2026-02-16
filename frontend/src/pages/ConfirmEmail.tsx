import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router";
import { useConfirmEmail } from "../orval/generated/user/user";
import { LoadingOverlay, Title } from "@mantine/core";

export default function ConfirmEmail() {
  const { token } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (token === undefined) {
    navigate("/login");
    return;
  }

  const {
    data,
    isPending
  } = useConfirmEmail(token, {
    query: {
      retry: false,
    },
  });

  if (data) {
    return <Title>{t("email.confirm.success")}</Title>;
  } else if (isPending) {
    <LoadingOverlay />;
  } else {
    return <Title>{t("email.confirm.invalid")}</Title>;
  }
}
