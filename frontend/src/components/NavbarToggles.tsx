import {
  Group,
  HoverCard,
  Text,
  useMantineColorScheme,
} from "@mantine/core";
import {
  IconLanguage,
  IconMoon,
  IconSun,
  IconSunMoon,
} from "@tabler/icons-react";
import { Button } from "@mantine/core";
import { useTranslation } from "react-i18next";

const NavbarToggles = () => {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const { t, i18n } = useTranslation();
  const changeLanguage = () => {
    const lng = i18n.language;
    if (lng === "en") {
      i18n.changeLanguage("de");
    } else {
      i18n.changeLanguage("en");
    }
  };

  return (
    <Group justify="center">
      <Button
        variant="transparent"
        leftSection={<IconLanguage />}
        onClick={changeLanguage}
      />
      <HoverCard
        shadow="md"
        withArrow
        openDelay={100}
        closeDelay={100}
        disabled={colorScheme == "auto"}
      >
        <HoverCard.Target>
          <Group>
            <Button
              darkHidden
              variant="transparent"
              leftSection={<IconMoon />}
              onClick={() => {
                setColorScheme("dark");
              }}
            />
            <Button
              lightHidden
              variant="transparent"
              leftSection={<IconSun />}
              onClick={() => {
                setColorScheme("light");
              }}
            />
          </Group>
        </HoverCard.Target>
        <HoverCard.Dropdown>
          <Group>
            <Text>{t("system-theme-follow")}</Text>
            <Button
              variant="transparent"
              leftSection={<IconSunMoon />}
              onClick={() => {
                setColorScheme("auto");
              }}
            />
          </Group>
        </HoverCard.Dropdown>
      </HoverCard>
    </Group>
  );
};

export default NavbarToggles;
