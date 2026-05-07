interface KpBoothZoneColorSwatchProps {
  color: string;
  size?: number;
  radius?: number;
}

export function KpBoothZoneColorSwatch({
  color,
  size = 12,
  radius = 4,
}: KpBoothZoneColorSwatchProps) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        backgroundColor: color,
        flexShrink: 0,
      }}
    />
  );
}
