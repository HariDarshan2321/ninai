import Link from "next/link";

export function Brand({ reversed = false }: { reversed?: boolean }) {
  return (
    <Link className="brand" href="/" aria-label="Ninai home">
      <img
        className="brand__wordmark"
        src={
          reversed
            ? "/assets/ninai-wordmark-reversed.svg"
            : "/assets/ninai-wordmark.svg"
        }
        alt="Ninai"
        width="640"
        height="257"
      />
    </Link>
  );
}
