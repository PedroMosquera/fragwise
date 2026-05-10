// Wisp — the chat persona. A small abstract SVG of a fragrance "scent
// trail": three soft curves rising from a vial-mouth shape, with a
// CSS keyframe that drifts the wisps upward + fades them. Two states:
// `idle` for static rest, `thinking` for the active streaming pulse.
//
// Pure presentation; no state of its own. Rendered inside the chat
// panel header and as the assistant message avatar.

type Props = {
  state?: "idle" | "thinking";
  size?: number;
  className?: string;
  ariaLabel?: string;
};

export function WispAvatar({
  state = "idle",
  size = 32,
  className,
  ariaLabel = "Wisp",
}: Props) {
  const animClass = state === "thinking" ? "wisp-trail-active" : "wisp-trail";
  return (
    <span
      role="img"
      aria-label={ariaLabel}
      className={className}
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <svg
        viewBox="0 0 32 32"
        width={size}
        height={size}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.4}
        strokeLinecap="round"
        aria-hidden
      >
        {/* vial mouth */}
        <path
          d="M11 24 Q16 28 21 24"
          strokeWidth={1.6}
          fill="none"
        />
        {/* three rising wisps */}
        <g className={animClass}>
          <path
            d="M13 22 Q11 18 13 14 Q15 11 13 7"
            opacity={0.85}
            style={{ animationDelay: "0s" }}
          />
          <path
            d="M16 22 Q18 17 16 12 Q14 8 16 4"
            opacity={0.95}
            style={{ animationDelay: "0.4s" }}
          />
          <path
            d="M19 22 Q21 19 19 15 Q17 11 19 7"
            opacity={0.7}
            style={{ animationDelay: "0.8s" }}
          />
        </g>
      </svg>
    </span>
  );
}
