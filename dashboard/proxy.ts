import { NextResponse, type NextRequest } from "next/server";

// Basic auth for every page and API route. Fails closed: unset credentials reject all requests.
// Same DEMO_USER / DEMO_PASSWORD as the hotline's /demo screen.

function unauthorized(): NextResponse {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="dashboard", charset="UTF-8"' },
  });
}

function safeEqual(a: string, b: string): boolean {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

export function proxy(request: NextRequest): NextResponse {
  const expectedUser = process.env.DEMO_USER;
  const expectedPassword = process.env.DEMO_PASSWORD;
  const header = request.headers.get("authorization");
  if (!expectedUser || !expectedPassword || !header?.startsWith("Basic ")) return unauthorized();

  let decoded: string;
  try {
    decoded = atob(header.slice("Basic ".length));
  } catch {
    return unauthorized();
  }
  const separator = decoded.indexOf(":");
  if (separator < 0) return unauthorized();
  const userOk = safeEqual(decoded.slice(0, separator), expectedUser);
  const passwordOk = safeEqual(decoded.slice(separator + 1), expectedPassword);
  return userOk && passwordOk ? NextResponse.next() : unauthorized();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
