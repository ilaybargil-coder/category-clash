const INVISIBLE_USERNAME_CHARACTERS = /[\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069]/g;

export function normalizeUsername(value: string): string {
  return value
    .normalize("NFKC")
    .replace(INVISIBLE_USERNAME_CHARACTERS, "")
    .trim();
}

export function isValidUsername(value: string): boolean {
  return /^[A-Za-z0-9_]{3,24}$/.test(normalizeUsername(value));
}
