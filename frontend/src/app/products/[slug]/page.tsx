import { permanentRedirect } from "next/navigation";
export default async function LegacyProduct({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  permanentRedirect(`/product/${encodeURIComponent((await params).slug)}`);
}
