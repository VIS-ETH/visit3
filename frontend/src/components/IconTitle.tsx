import { ThemeIcon, Title } from "@mantine/core";
import type { ReactNode } from "react";

interface IconTitleProps {
  icon: ReactNode;
  title: string;
  color: string;
  iconSize?: number;
  titleOrder?: 1 | 2 | 3 | 4 | 5 | 6;
}

const IconTitle = ({
  icon,
  title,
  color,
  iconSize = 80,
  titleOrder = 2,
}: IconTitleProps) => {
  return (
    <>
      <ThemeIcon size={iconSize} radius="xl" variant="light" color={color}>
        {icon}
      </ThemeIcon>
      <Title order={titleOrder} ta="center">
        {title}
      </Title>
    </>
  );
};
export default IconTitle;
