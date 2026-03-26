type PulseIndicatorProps = {
  className?: string;
};

export function PulseIndicator({ className }: PulseIndicatorProps) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-1 w-1 animate-pulse-slow bg-surface-tint ${className ?? ""}`}
    />
  );
}
