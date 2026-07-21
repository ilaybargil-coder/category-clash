const AVATAR_COUNT = 40;

export function avatarSrc(seed: string): string {
  if (!seed) {
    return "/assets/avatars/avatar-01.png";
  }

  let hash = 5381;

  for (let index = 0; index < seed.length; index += 1) {
    hash = ((hash << 5) + hash) ^ seed.charCodeAt(index);
  }

  const avatarIndex = (hash >>> 0) % AVATAR_COUNT + 1;
  return `/assets/avatars/avatar-${String(avatarIndex).padStart(2, "0")}.png`;
}

export function avatarSrcFor(
  avatarKey: string | null | undefined,
  seed: string
): string {
  if (avatarKey) {
    return `/assets/avatars/${avatarKey}.png`;
  }

  return avatarSrc(seed);
}
