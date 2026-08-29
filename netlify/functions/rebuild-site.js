const SUPABASE_URL =
  process.env.SUPABASE_URL || "https://twxhcmvzbpnrneywdece.supabase.co";
const SUPABASE_PUBLISHABLE_KEY =
  process.env.SUPABASE_PUBLISHABLE_KEY ||
  "sb_publishable_IHIMbYQacziyL1GcU6Mdtw_7AQdaCWg";

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return json(405, { error: "method_not_allowed" });
  }

  const auth = event.headers.authorization || event.headers.Authorization || "";
  if (!auth.startsWith("Bearer ")) {
    return json(401, { error: "missing_session" });
  }

  const admin = await isAdmin(auth);
  if (!admin) {
    return json(403, { error: "not_authorized" });
  }

  const hookUrl = process.env.NETLIFY_BUILD_HOOK_URL;
  if (!hookUrl) {
    return json(503, { error: "build_hook_not_configured" });
  }

  const response = await fetch(hookUrl, { method: "POST" });
  if (!response.ok) {
    return json(502, { error: "build_hook_failed" });
  }

  return json(202, { ok: true });
};

async function isAdmin(auth) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/is_admin`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      Authorization: auth,
      "Content-Type": "application/json",
    },
    body: "{}",
  });

  if (!response.ok) {
    return false;
  }
  return Boolean(await response.json());
}

function json(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(body),
  };
}
