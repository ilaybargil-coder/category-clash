export type AvatarParams = {
  bgColor1: string;
  bgColor2: string;
  faceColor: string;
  eyeColor: string;
  shapeType: "circle" | "triangle" | "diamond" | "blob";
  shapeX: number;
  shapeY: number;
  shapeScale: number;
  accentColor: string;
};

const GRADIENTS = [
  ["#312E81", "#7C3AED"],
  ["#4C1D95", "#DB2777"],
  ["#134E4A", "#0D9488"],
  ["#881337", "#E11D48"],
  ["#78350F", "#D97706"],
  ["#365314", "#65A30D"],
  ["#0C4A6E", "#0284C7"],
] as const;

const FACE_COLORS = [
  "#FDE68A",
  "#FBCFE8",
  "#C4B5FD",
  "#99F6E4",
  "#BAE6FD",
  "#D9F99D",
  "#FED7AA",
] as const;

const EYE_COLORS = ["#1E1B4B", "#172554", "#292524", "#3B0764"] as const;
const ACCENT_COLORS = [
  "#A78BFA",
  "#2DD4BF",
  "#FB7185",
  "#FBBF24",
  "#A3E635",
  "#38BDF8",
  "#818CF8",
] as const;
const SHAPES: AvatarParams["shapeType"][] = [
  "circle",
  "triangle",
  "diamond",
  "blob",
];

function hashSeed(seed: string): number {
  let hash = 5381;

  for (let index = 0; index < seed.length; index += 1) {
    hash = ((hash << 5) + hash) ^ seed.charCodeAt(index);
  }

  return hash >>> 0;
}

function createRandom(seed: number): () => number {
  let state = seed || 1;

  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return (state >>> 0) / 4294967296;
  };
}

export function generateAvatar(seed: string): AvatarParams {
  const random = createRandom(hashSeed(seed));
  const gradient = GRADIENTS[Math.floor(random() * GRADIENTS.length)];

  return {
    bgColor1: gradient[0],
    bgColor2: gradient[1],
    faceColor: FACE_COLORS[Math.floor(random() * FACE_COLORS.length)],
    eyeColor: EYE_COLORS[Math.floor(random() * EYE_COLORS.length)],
    shapeType: SHAPES[Math.floor(random() * SHAPES.length)],
    shapeX: 30 + Math.round(random() * 4),
    shapeY: 31 + Math.round(random() * 4),
    shapeScale: 0.84 + Math.round(random() * 12) / 100,
    accentColor: ACCENT_COLORS[Math.floor(random() * ACCENT_COLORS.length)],
  };
}
