export default function SelectionBox({
  rect,
}: {
  rect: { x: number; y: number; w: number; h: number } | null;
}) {
  if (!rect || (rect.w < 2 && rect.h < 2)) return null;
  return (
    <div
      className="ws-selection-marquee"
      style={{
        left: rect.x,
        top: rect.y,
        width: rect.w,
        height: rect.h,
      }}
    />
  );
}
