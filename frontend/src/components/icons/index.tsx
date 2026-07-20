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
      fill="currentColor"
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
      <path
        fillOpacity={0.24}
        d="M4 5.25A1.25 1.25 0 0 1 5.25 4H8v2.5H6.5v.75A3.75 3.75 0 0 0 9.37 10.9l.51 2.45A6.25 6.25 0 0 1 4 7.25v-2Zm16 0v2a6.25 6.25 0 0 1-5.88 6.1l.51-2.45a3.75 3.75 0 0 0 2.87-3.65V6.5H16V4h2.75A1.25 1.25 0 0 1 20 5.25Z"
      />
      <path d="M7.25 3h9.5v5.25a4.75 4.75 0 1 1-9.5 0V3ZM10.75 14.64h2.5V18h2.25A1.5 1.5 0 0 1 17 19.5V21H7v-1.5A1.5 1.5 0 0 1 8.5 18h2.25v-3.36Z" />
    </IconBase>
  );
}

export function TargetIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" fillOpacity={0.24} />
      <path
        fillRule="evenodd"
        d="M12 6.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11Zm0 3a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z"
        clipRule="evenodd"
      />
      <circle cx="12" cy="12" r="1.5" />
      <path d="M10.75 1h2.5v4h-2.5V1Zm0 18h2.5v4h-2.5v-4ZM1 10.75h4v2.5H1v-2.5Zm18 0h4v2.5h-4v-2.5Z" />
    </IconBase>
  );
}

export function GamepadIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        fillOpacity={0.24}
        d="M8.25 5h7.5a6 6 0 0 1 5.78 4.4l1.16 4.2a4.2 4.2 0 0 1-7.25 3.77L14.2 16H9.8l-1.24 1.37A4.2 4.2 0 0 1 1.31 13.6l1.16-4.2A6 6 0 0 1 8.25 5Z"
      />
      <rect x="6.25" y="8.25" width="2.5" height="7.5" rx="1.25" />
      <rect x="3.75" y="10.75" width="7.5" height="2.5" rx="1.25" />
      <circle cx="16.25" cy="10" r="1.5" />
      <circle cx="19" cy="13" r="1.5" />
    </IconBase>
  );
}

export function JokerIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="4" y="2" width="16" height="20" rx="3" fillOpacity={0.24} />
      <path d="m12 6 1.52 3.08 3.4.5-2.46 2.4.58 3.38L12 13.76l-3.04 1.6.58-3.38-2.46-2.4 3.4-.5L12 6Z" />
      <circle cx="7.25" cy="18.75" r="1.25" />
      <circle cx="16.75" cy="5.25" r="1.25" />
    </IconBase>
  );
}

export function SwapIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        fillOpacity={0.24}
        d="M5 5h9.5a5.5 5.5 0 0 1 5.5 5.5V12h-3v-1.5A2.5 2.5 0 0 0 14.5 8H5V5Zm14 14H9.5A5.5 5.5 0 0 1 4 13.5V12h3v1.5A2.5 2.5 0 0 0 9.5 16H19v3Z"
      />
      <path d="m15.25 2.75 4.72 3.47a1 1 0 0 1 0 1.56l-4.72 3.47V2.75ZM8.75 21.25l-4.72-3.47a1 1 0 0 1 0-1.56l4.72-3.47v8.5Z" />
    </IconBase>
  );
}

export function TimerIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="13" r="9" fillOpacity={0.24} />
      <rect x="9" y="1" width="6" height="3" rx="1.5" />
      <path d="M10.75 6h2.5v7.35l4.15 2.4-1.25 2.16-4.78-2.76a1.25 1.25 0 0 1-.62-1.08V6Zm6.84-.18 2.12-2.12 2.12 2.12-2.12 2.12-2.12-2.12Z" />
      <circle cx="12" cy="13" r="1.75" />
    </IconBase>
  );
}

export function SoundOnIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 9h3.28l4.55-3.79A1.32 1.32 0 0 1 13 6.22v11.56a1.32 1.32 0 0 1-2.17 1.01L6.28 15H3a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2Z" />
      <path
        fillOpacity={0.24}
        d="M15.18 8.82a1.5 1.5 0 0 1 2.12 0 4.5 4.5 0 0 1 0 6.36 1.5 1.5 0 1 1-2.12-2.12 1.5 1.5 0 0 0 0-2.12 1.5 1.5 0 0 1 0-2.12Zm3.62-3.63a1.5 1.5 0 0 1 2.12 0 9.63 9.63 0 0 1 0 13.62 1.5 1.5 0 1 1-2.12-2.12 6.63 6.63 0 0 0 0-9.38 1.5 1.5 0 0 1 0-2.12Z"
      />
    </IconBase>
  );
}

export function SoundOffIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 9h3.28l4.55-3.79A1.32 1.32 0 0 1 13 6.22v11.56a1.32 1.32 0 0 1-2.17 1.01L6.28 15H3a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2Z" />
      <circle cx="18.5" cy="12" r="5" fillOpacity={0.24} />
      <path d="m16.03 7.91 2.47 2.47 2.47-2.47 1.62 1.62L20.12 12l2.47 2.47-1.62 1.62-2.47-2.47-2.47 2.47-1.62-1.62L16.88 12l-2.47-2.47 1.62-1.62Z" />
    </IconBase>
  );
}

export function ShareIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="M12.75 5h5.5c.97 0 1.75.78 1.75 1.75v5.5h-3V9.62l-7.94 7.94-2.12-2.12L14.38 8h-1.63V5Z" />
    </IconBase>
  );
}

export function CoinIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <circle cx="12" cy="12" r="7.25" fillOpacity={0.24} />
      <path d="M10.75 5.5h2.5v1.27c1.41.25 2.56.94 3.37 1.8l-1.82 1.71c-.69-.74-1.61-1.16-2.76-1.16-1.05 0-1.72.35-1.72.83 0 .55.76.76 2.27.99 2.17.34 4.16 1.06 4.16 3.3 0 1.7-1.37 2.84-3.5 3.12v1.14h-2.5v-1.2a6.4 6.4 0 0 1-3.63-1.86l1.82-1.71c.85.87 1.91 1.31 3.18 1.31 1.18 0 1.88-.33 1.88-.8 0-.54-.76-.78-2.32-1.03-2.12-.33-4.11-1.04-4.11-3.26 0-1.65 1.26-2.81 3.18-3.14V5.5Z" />
    </IconBase>
  );
}

export function MedalIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path fillOpacity={0.24} d="M5 2h5l3.5 8H8.2L5 2Zm9 0h5l-3.2 8h-5.3L14 2Z" />
      <circle cx="12" cy="15" r="7" />
      <path
        fillOpacity={0.24}
        d="m12 10.5 1.39 2.82 3.11.45-2.25 2.19.53 3.1L12 17.6l-2.78 1.46.53-3.1-2.25-2.19 3.11-.45L12 10.5Z"
      />
    </IconBase>
  );
}

export function FlameIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        fillOpacity={0.24}
        d="M12.46 1.82a1 1 0 0 1 1.08.13C17.82 5.41 21 9.14 21 14.2A9 9 0 0 1 3 14c0-3.4 1.73-6.5 4.08-8.76a1 1 0 0 1 1.65.42c.34 1.04.8 1.9 1.5 2.53 1.35-1.53 1.52-3.49 1.7-5.55a1 1 0 0 1 .53-.82Z"
      />
      <path d="M12.37 10.55c.28-.74.42-1.56.5-2.36 2.1 1.83 4.13 3.9 4.13 6.69a5 5 0 0 1-10 0c0-1.58.74-3.1 1.77-4.33.45.87 1.05 1.61 1.87 2.18a1 1 0 0 0 1.46-.38c.1-.2.19-.41.27-.62v-1.18Z" />
    </IconBase>
  );
}

export function LightbulbIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        fillOpacity={0.24}
        d="M12 3a7 7 0 0 1 4.41 12.44c-.76.62-1.16 1.24-1.16 1.81v.25h-6.5v-.25c0-.57-.4-1.19-1.16-1.81A7 7 0 0 1 12 3Z"
      />
      <path d="M10.5 16h3v-3.38l2.35-2.35-2.12-2.12L12 9.88l-1.73-1.73-2.12 2.12 2.35 2.35V16Zm-2 2.5h7v1.25A2.25 2.25 0 0 1 13.25 22h-2.5a2.25 2.25 0 0 1-2.25-2.25V18.5ZM10.75 0h2.5v2h-2.5V0ZM2.9 4.66 4.67 2.9l1.41 1.42-1.76 1.76L2.9 4.66Zm14.99-.34 1.41-1.41 1.77 1.76-1.42 1.42-1.76-1.77ZM0 10.75h3v2.5H0v-2.5Zm21 0h3v2.5h-3v-2.5Z" />
    </IconBase>
  );
}

export function LosesIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="m8.1 6.34 3.9 3.9 3.9-3.9 1.76 1.76-3.9 3.9 3.9 3.9-1.76 1.76-3.9-3.9-3.9 3.9-1.76-1.76 3.9-3.9-3.9-3.9L8.1 6.34Z" />
    </IconBase>
  );
}

export function AccuracyIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="7.5" fillOpacity={0.24} />
      <path d="M10.75 1h2.5v5h-2.5V1Zm0 17h2.5v5h-2.5v-5ZM1 10.75h5v2.5H1v-2.5Zm17 0h5v2.5h-5v-2.5Z" />
      <circle cx="12" cy="12" r="3.25" />
      <circle cx="12" cy="12" r="1.25" fillOpacity={0.24} />
    </IconBase>
  );
}

export function LightningIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="M13.35 1.75a1 1 0 0 1 1.76.8l-.92 6.2h4.56a1 1 0 0 1 .77 1.64l-9 10.86a1 1 0 0 1-1.76-.8l.92-6.2H5.25a1 1 0 0 1-.78-1.63l8.88-10.87Z" />
    </IconBase>
  );
}

export function WaveIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        fillOpacity={0.24}
        d="M18.6 2.25a1.15 1.15 0 0 1 1.5.63l.9 2.17-2.12.88-.9-2.18a1.15 1.15 0 0 1 .62-1.5Zm2.25 5.13 2.2-.65.66 2.25-2.2.65-.66-2.25Z"
      />
      <rect x="7.25" y="2.5" width="3" height="10" rx="1.5" transform="rotate(-15 8.75 7.5)" />
      <rect x="10.25" y="1" width="3" height="11" rx="1.5" transform="rotate(-8 11.75 6.5)" />
      <rect x="13.25" y="1.5" width="3" height="10.5" rx="1.5" transform="rotate(3 14.75 6.75)" />
      <rect x="16" y="3.25" width="3" height="9" rx="1.5" transform="rotate(12 17.5 7.75)" />
      <path d="M4.25 9.03a1.55 1.55 0 0 1 2.12.57l2.17 3.76.27-1.54a3 3 0 0 1 3.48-2.43l.98.17a1.4 1.4 0 0 1 1.14 1.62 1.4 1.4 0 0 1-1.62 1.14l-.98-.17-.52 2.95a1.5 1.5 0 0 1-2.77.48L6.75 12.5l.9 3.35a4.8 4.8 0 0 0 5.9 3.4l.76-.2a5.25 5.25 0 0 0 3.72-6.43l-.53-1.97 3-.8.53 1.96a8.35 8.35 0 0 1-5.91 10.2l-.76.2a7.9 7.9 0 0 1-9.69-5.57L3.58 12.6l.1-1.7a1.55 1.55 0 0 1 .57-1.87Z" />
    </IconBase>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="m9.65 17.75-5.4-5.4 2.12-2.12 3.28 3.28 7.98-7.98 2.12 2.12-10.1 10.1Z" />
    </IconBase>
  );
}

export function SimilarIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="M4.52 8.98C6.06 7.3 7.66 6.5 9.4 6.6c1.48.08 2.65.78 3.68 1.4 1 .6 1.78 1.06 2.68 1.1.89.04 1.78-.34 2.86-1.28l1.96 2.26c-1.54 1.34-3.2 2.1-4.96 2.02-1.67-.08-2.94-.84-4.09-1.52-.91-.55-1.6-.96-2.3-1-.72-.04-1.52.35-2.5 1.42L4.52 8.98Zm0 6C6.06 13.3 7.66 12.5 9.4 12.6c1.48.08 2.65.78 3.68 1.4 1 .6 1.78 1.06 2.68 1.1.89.04 1.78-.34 2.86-1.28l1.96 2.26c-1.54 1.34-3.2 2.1-4.96 2.02-1.67-.08-2.94-.84-4.09-1.52-.91-.55-1.6-.96-2.3-1-.72-.04-1.52.35-2.5 1.42l-2.21-2.02Z" />
    </IconBase>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <path d="m11.06 4.94 2.12 2.12-3.44 3.44H20v3H9.74l3.44 3.44-2.12 2.12L4 12l7.06-7.06Z" />
    </IconBase>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" fillOpacity={0.24} />
      <rect x="10.5" y="5" width="3" height="14" rx="1.5" />
      <rect x="5" y="10.5" width="14" height="3" rx="1.5" />
    </IconBase>
  );
}
