export const Skeleton = ({ className = "" }: { className?: string }) => (
  <span className={`skeleton ${className}`} aria-label="Loading" />
);
