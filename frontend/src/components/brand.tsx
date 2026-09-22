import Image from "next/image";
import Link from "next/link";
export default function Brand({ footer = false }: { footer?: boolean }) {
  return (
    <Link
      href="/"
      className={`sanctuary-brand${footer ? " sanctuary-brand-footer" : ""}`}
      aria-label="Your Sanctuary home — Beautiful spaces. Happier living."
    >
      <span className="brand-sign">
        <span className="ys-monogram" aria-hidden="true">
          <Image
            src="/brand/ys-monogram.png"
            alt=""
            width={1536}
            height={1024}
            sizes="120px"
          />
        </span>
        <span className="sanctuary-wordmark">
          <span className="sanctuary-name">Your Sanctuary</span>
          <span className="sanctuary-tagline">
            Beautiful spaces. Happier living.
          </span>
        </span>
      </span>
    </Link>
  );
}
