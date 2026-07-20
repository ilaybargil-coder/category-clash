import type * as React from "react";

export interface IconProps {
  className?: string;
  size?: number;
  style?: React.CSSProperties;
}

interface IconBaseProps extends IconProps {
  children: React.ReactNode;
}

function IconBase({ className, size, style, children }: IconBaseProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size ?? 24}
      height={size ?? 24}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function TrophyIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M8 4h8v5a4 4 0 0 1-8 0V4Z" />
      <path d="M8 6H5v1a4 4 0 0 0 4 4" />
      <path d="M16 6h3v1a4 4 0 0 1-4 4" />
      <path d="M12 13v4" />
      <path d="M8 21h8" />
      <path d="M9 17h6v4H9z" />
    </IconBase>
  );
}

export function TargetIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3" />
      <path d="M12 19v3" />
      <path d="M2 12h3" />
      <path d="M19 12h3" />
    </IconBase>
  );
}

export function GamepadIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M8.5 6h7a5 5 0 0 1 4.8 3.6l1.3 4.7a3 3 0 0 1-5.2 2.7l-1.5-2H9.1l-1.5 2a3 3 0 0 1-5.2-2.7l1.3-4.7A5 5 0 0 1 8.5 6Z" />
      <path d="M7 10v4" />
      <path d="M5 12h4" />
      <circle cx="16.5" cy="10.5" r=".5" fill="currentColor" stroke="none" />
      <circle cx="18.5" cy="13" r=".5" fill="currentColor" stroke="none" />
    </IconBase>
  );
}

export function JokerIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="m12 7 1.1 2.2 2.4.3-1.7 1.7.4 2.4-2.2-1.1-2.2 1.1.4-2.4-1.7-1.7 2.4-.3L12 7Z" />
      <path d="M8 17h.01" />
      <path d="M16 7h.01" />
    </IconBase>
  );
}

export function SwapIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M20 7h-9a4 4 0 0 0-4 4" />
      <path d="m17 4 3 3-3 3" />
      <path d="M4 17h9a4 4 0 0 0 4-4" />
      <path d="m7 20-3-3 3-3" />
    </IconBase>
  );
}

export function TimerIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l2.5 1.5" />
      <path d="M9 2h6" />
      <path d="M12 2v3" />
      <path d="m18 6 1.5-1.5" />
    </IconBase>
  );
}

export function SoundOnIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M11 5 6 9H3v6h3l5 4V5Z" />
      <path d="M15 9a4 4 0 0 1 0 6" />
      <path d="M18 6a8 8 0 0 1 0 12" />
    </IconBase>
  );
}

export function SoundOffIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M11 5 6 9H3v6h3l5 4V5Z" />
      <path d="m15 10 6 6" />
      <path d="m21 10-6 6" />
    </IconBase>
  );
}

export function ShareIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M7 17 17 7" />
      <path d="M8 7h9v9" />
    </IconBase>
  );
}

export function CoinIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M15 8.5c-.7-.7-1.7-1-3-1-1.7 0-3 .9-3 2s1.3 1.8 3 2c1.7.2 3 1 3 2s-1.3 2-3 2c-1.3 0-2.4-.4-3-1" />
      <path d="M12 5.5v13" />
    </IconBase>
  );
}

export function MedalIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M8 3h8l-2 6h-4L8 3Z" />
      <path d="m8 3 4 6 4-6" />
      <circle cx="12" cy="15" r="5" />
      <path d="m12 12.5.8 1.6 1.7.2-1.2 1.2.3 1.7-1.6-.8-1.6.8.3-1.7-1.2-1.2 1.7-.2.8-1.6Z" />
    </IconBase>
  );
}

export function FlameIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 22a7 7 0 0 0 7-7c0-4-2.5-7-6-10 .2 3-1.5 4.5-3 5.5-.2-2-1.2-3.5-2.5-4.5C7 10 5 11.5 5 15a7 7 0 0 0 7 7Z" />
      <path d="M9.5 17a2.5 2.5 0 0 0 5 0c0-1.5-.8-2.6-2-3.7 0 1.2-.7 1.8-1.3 2.3-.2-.8-.6-1.4-1.2-1.9-.1 1.4-.5 2.1-.5 3.3Z" />
    </IconBase>
  );
}

export function LightbulbIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9 18h6" />
      <path d="M10 22h4" />
      <path d="M8.5 15.5A6 6 0 1 1 15.5 15.5C14.6 16.2 14 17 14 18h-4c0-1-.6-1.8-1.5-2.5Z" />
      <path d="M12 2V1" />
      <path d="m4.9 4.9-.7-.7" />
      <path d="M2 12H1" />
      <path d="m19.1 4.9.7-.7" />
      <path d="M22 12h1" />
    </IconBase>
  );
}

export function LosesIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="m9 9 6 6" />
      <path d="m15 9-6 6" />
    </IconBase>
  );
}

export function AccuracyIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="7" />
      <circle cx="12" cy="12" r="2" />
      <path d="M12 2v3" />
      <path d="M12 19v3" />
      <path d="M2 12h3" />
      <path d="M19 12h3" />
    </IconBase>
  );
}

export function LightningIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="m13 2-8 12h7l-1 8 8-12h-7l1-8Z" />
    </IconBase>
  );
}

export function WaveIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M7.5 12.5 6 9.8a1.3 1.3 0 0 0-2.3 1.3l3.6 6.3A7 7 0 0 0 19.8 11l-1.5-5.6a1.3 1.3 0 0 0-2.5.7l.8 3" />
      <path d="m16.6 9.1-1.5-5.4a1.3 1.3 0 0 0-2.5.7l1.2 4.5" />
      <path d="m13.8 8.9-1.5-5.3a1.3 1.3 0 0 0-2.5.7l1.4 5" />
      <path d="m11.2 9.3-1.1-4a1.3 1.3 0 0 0-2.5.7l1.8 6.4" />
      <path d="M19 3.5c.9.3 1.6 1 2 1.9" />
    </IconBase>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="m5 12 4 4L19 6" />
    </IconBase>
  );
}

export function SimilarIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 9c2-2 4-2 7 0s5 2 7 0" />
      <path d="M5 15c2-2 4-2 7 0s5 2 7 0" />
    </IconBase>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </IconBase>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </IconBase>
  );
}
