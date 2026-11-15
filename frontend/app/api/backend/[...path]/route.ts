import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const binding = process.env.BACKEND_URL;
  if (!binding) return NextResponse.json({ detail: "Private BACKEND_URL service binding is not configured." }, { status: 503 });
  const { path } = await context.params;
  if (!path?.length || path.some((part) => part === ".." || part.includes("\\"))) {
    return NextResponse.json({ detail: "Invalid API route." }, { status: 400 });
  }
  const target = `${binding.replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  try {
    const response = await fetch(target, {
      method: request.method,
      headers: request.method === "POST" ? { "content-type": request.headers.get("content-type") ?? "application/json" } : undefined,
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
      cache: "no-store",
    });
    const headers = new Headers();
    for (const name of ["content-type", "content-disposition", "cache-control", "x-request-id"]) {
      const value = response.headers.get(name);
      if (value) headers.set(name, value);
    }
    headers.set("cache-control", "no-store");
    return new Response(response.body, { status: response.status, headers });
  } catch {
    return NextResponse.json({ detail: "The private scientific backend could not be reached." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
