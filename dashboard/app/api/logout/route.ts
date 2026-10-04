export const dynamic = "force-dynamic";

export function GET() {
  return new Response("<!doctype html><title>Signed out</title><p>Signed out. Close this tab or reload to sign in again.</p>", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="dashboard"', "Content-Type": "text/html; charset=utf-8" },
  });
}
