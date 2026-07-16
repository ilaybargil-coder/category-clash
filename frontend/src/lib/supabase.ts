import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export const AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "demo";
export const SUPABASE_AUTH_ENABLED = AUTH_MODE === "supabase";
export const SUPABASE_AUTH_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
);

let client: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!SUPABASE_AUTH_ENABLED || !url || !publishableKey) {
    throw new Error("Supabase Auth is not configured");
  }
  client ??= createClient(url, publishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
  return client;
}
