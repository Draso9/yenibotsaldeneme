import Image from "next/image";

type IzfinBrandMarkProps = {
  className?: string;
  decorative?: boolean;
  imageSize?: number;
  priority?: boolean;
};

export function IzfinBrandMark({
  className = "",
  decorative = false,
  imageSize = 72,
  priority = false,
}: Readonly<IzfinBrandMarkProps>) {
  return <div
    aria-hidden={decorative ? true : undefined}
    className={`izfin-brand-mark ${className}`.trim()}
  >
    <Image
      alt={decorative ? "" : "IZFIN"}
      height={imageSize}
      priority={priority}
      src="/brand/izfin-logo.png"
      width={imageSize}
    />
  </div>;
}
