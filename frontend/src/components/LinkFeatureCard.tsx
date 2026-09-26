import { Card, Image, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import type { ReactNode } from "react";

export interface FeatureImage {
  src: string;
  srcSet: string;
  width: number;
  height: number;
}

interface LinkFeatureCardProps {
  to: string;
  image: FeatureImage;
  imageAlt: string;
  title: string;
  description: string;
  action?: ReactNode;
}

const IMAGE_SIZES = "(max-width: 1100px) 100vw, 1060px";

const LinkFeatureCard = ({
  to,
  image,
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
      padding="lg"
      style={{
        boxShadow: "var(--visit-feature-shadow)",
      }}
    >
      <Card.Section>
        <Image
          src={image.src}
          srcSet={image.srcSet}
          sizes={IMAGE_SIZES}
          width={image.width}
          height={image.height}
          alt={imageAlt}
          h="auto"
          fit="contain"
          style={{ aspectRatio: `${image.width} / ${image.height}` }}
        />
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
