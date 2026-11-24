import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";


const TOKEN_COOKIE = "documind_access";
const PROFILE_COOKIE = "documind_profile";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function backendUrl(): string {
  return (
    process.env.BACKEND_INTERNAL_URL?.replace(/\/+$/, "") ||
    "http://127.0.0.1:8000"
  );
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

async function proxy(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  const { path } = await context.params;
  const endpoint = path.join("/");
  const cookieStore = await cookies();

  if (endpoint === "auth/session" && request.method === "GET") {
    const token = cookieStore.get(TOKEN_COOKIE)?.value;
    const profileValue = cookieStore.get(PROFILE_COOKIE)?.value;

    if (!token || !profileValue) {
      return NextResponse.json({ authenticated: false, profile: null });
    }

    try {
      return NextResponse.json({
        authenticated: true,
        profile: JSON.parse(
          Buffer.from(profileValue, "base64url").toString("utf8"),
        ),
      });
    } catch {
      return NextResponse.json({ authenticated: false, profile: null });
    }
  }

  if (endpoint === "auth/logout" && request.method === "POST") {
    const response = NextResponse.json({ message: "Logged out." });
    response.cookies.set(TOKEN_COOKIE, "", cookieOptions(0));
    response.cookies.set(PROFILE_COOKIE, "", cookieOptions(0));
    return response;
  }

  const target = `${backendUrl()}/${path
    .map((part) => encodeURIComponent(part))
    .join("/")}${request.nextUrl.search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");

  if (contentType) headers.set("content-type", contentType);
  headers.set("accept", "application/json");

  const accessToken = cookieStore.get(TOKEN_COOKIE)?.value;
  if (accessToken) {
    headers.set("authorization", `Bearer ${accessToken}`);
  }

  const method = request.method;
  const body =
    method === "GET" || method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  let backendResponse: Response;

  try {
    backendResponse = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "The backend service is unavailable." },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  const responseContentType = backendResponse.headers.get("content-type");
  const contentDisposition = backendResponse.headers.get("content-disposition");

  if (responseContentType) {
    responseHeaders.set("content-type", responseContentType);
  }

  if (contentDisposition) {
    responseHeaders.set("content-disposition", contentDisposition);
  }

  responseHeaders.set("cache-control", "no-store");

  const isAuthentication =
    endpoint === "auth/login" || endpoint === "auth/register";

  if (isAuthentication && backendResponse.ok) {
    const result = (await backendResponse.json()) as Record<string, unknown>;

    if (
      typeof result.access_token !== "string" ||
      typeof result.expires_in !== "number"
    ) {
      return NextResponse.json(
        { detail: "The authentication response was invalid." },
        { status: 502 },
      );
    }

    const { access_token: token, expires_in: expiresIn, ...profile } = result;
    const maxAge = Math.max(0, Math.floor(expiresIn));

    const response = NextResponse.json(profile, {
      status: backendResponse.status,
    });

    response.cookies.set(TOKEN_COOKIE, token, cookieOptions(maxAge));
    response.cookies.set(
      PROFILE_COOKIE,
      Buffer.from(JSON.stringify(profile)).toString("base64url"),
      cookieOptions(maxAge),
    );

    return response;
  }

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

