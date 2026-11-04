// The same backend EzyMailer's desktop app itself logs into - baked in at
// build time so the fallback login form (opening this page directly,
// without going through the "Mail Validator" button) authenticates against
// the real account system rather than a hardcoded dev value.
const EZYMAILER_API_URL = process.env.NEXT_PUBLIC_EZYMAILER_API_URL || "http://15.206.161.73:8765";

export async function loginToEzyMailer(username: string, password: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${EZYMAILER_API_URL}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new Error("Could not reach EzyMailer - check your connection and try again.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "Invalid username or password.");
  }
  if (typeof data?.access_token !== "string" || !data.access_token) {
    throw new Error("Login succeeded but no token was returned.");
  }
  return data.access_token;
}
