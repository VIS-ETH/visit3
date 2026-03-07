import { ActionIcon } from "@mantine/core";
import { IconArrowBackUp } from "@tabler/icons-react";
import { Link } from "react-router";

interface BackButtonProps {
  to: string;
}

const BackButton = ({ to }: BackButtonProps) => {
  return (
    <ActionIcon
      radius="md"
      size="input-md"
      component={Link}
      to={to}
      variant="transparent"
    >
      <IconArrowBackUp />
    </ActionIcon>
  );
};
export default BackButton;
