import { NextResponse, type NextRequest } from "next/server";

// Resolve retired collection links before streaming can send a 200 response.
export function proxy(request: NextRequest) {
  if (!request.nextUrl.searchParams.has("featured")) return NextResponse.next();
  const destination = request.nextUrl.clone();
  destination.searchParams.delete("featured");
  destination.searchParams.set("on_sale", "true");
  return NextResponse.redirect(destination, 308);
}

export const config = { matcher: "/shop" };
