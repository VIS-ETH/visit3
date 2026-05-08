import { Card, Image, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import type { ReactNode } from "react";

interface LinkFeatureCardProps {
  to: string;
  imageSrc: string;
  imageAlt: string;
  title: string;
  description: string;
  action?: ReactNode;
}

const LinkFeatureCard = ({
  to,
  imageSrc,
  imageAlt,
  title,
  description,
  action,
}: LinkFeatureCardProps) => {
  return (
    <Card
      component={Link}
      to={to}
      withBorder
      radius="lg"
      p="lg"
      style={{
        borderColor: "var(--visit-border)",
        boxShadow: "var(--visit-feature-shadow)",
      }}
    >
      <Card.Section>
        <Image src={imageSrc} alt={imageAlt} h={180} />
      </Card.Section>
      <Stack gap={6} mt="md">
        <Title order={4} className="section-title">
          {title}
        </Title>
        <Text size="sm" c="dimmed">
          {description}
        </Text>
        {action}
      </Stack>
    </Card>
  );
};
export default LinkFeatureCard;
