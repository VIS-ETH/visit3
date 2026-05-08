interface KpBoothZoneColorSwatchProps {
  color: string;
  size?: number;
  radius?: number;
}

export const KpBoothZoneColorSwatch = ({
  color,
  size = 12,
  radius = 4,
}: KpBoothZoneColorSwatchProps) => {
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
};
export default KpBoothZoneColorSwatch;
