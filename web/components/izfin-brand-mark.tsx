import Image from "next/image";

type IzfinBrandMarkProps = {
  decorative?: boolean;
  priority?: boolean;
};

export function IzfinBrandMark({
  decorative = false,
  priority = false,
}: Readonly<IzfinBrandMarkProps>) {
  return <div
    aria-hidden={decorative ? true : undefined}
    className="izfin-brand-mark"
  >
    <Image
      alt={decorative ? "" : "IZFIN"}
      height={72}
      priority={priority}
      src="/brand/izfin-logo.png"
      width={72}
    />
  </div>;
}
