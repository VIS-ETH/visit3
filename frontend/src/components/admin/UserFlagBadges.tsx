import { Badge, Group } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";

const UserFlagBadges = ({ user }: { user: UserResponse }) => {
  const { t } = useTranslation();

  const flags: string[] = [];
  if (user.is_admin) flags.push("user_management.flags.admin");
  if (user.is_staff) flags.push("user_management.flags.staff");
  if (user.is_kp_president) flags.push("user_management.flags.president");
  if (user.is_company) flags.push("user_management.flags.company");

  if (flags.length === 0) {
    return (
      <Badge color="gray" variant="light">
        {t("user_management.flags.none")}
      </Badge>
    );
  }

  return (
    <Group gap="xs" wrap="wrap">
      {flags.map((flag) => (
        <Badge key={flag} variant="light">
          {t(flag)}
        </Badge>
      ))}
    </Group>
  );
};

export default UserFlagBadges;
