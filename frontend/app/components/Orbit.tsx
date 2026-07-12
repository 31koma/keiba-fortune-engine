"use client";

/** 4者(馬・騎手・レース日・あなた)の軌道が一点で交わるブランド図。
 *  ロゴ思想「交差」のUI表現。userActiveで「あなた」がゴールドに灯る。 */
export default function Orbit({ userActive }: { userActive: boolean }) {
  const ink = "rgba(245,241,232,0.85)";
  const dim = "rgba(245,241,232,0.35)";
  const gold = "#c9a45c";
  const nodes = [
    { x: 160, y: 34, label: "競走馬", active: true },
    { x: 286, y: 160, label: "騎手", active: true },
    { x: 160, y: 286, label: "レース日", active: true },
    { x: 34, y: 160, label: "あなた", active: userActive },
  ];
  return (
    <svg viewBox="0 0 320 320" role="img" aria-label="馬・騎手・レース日・あなたの4者の関係図">
      <circle cx="160" cy="160" r="126" fill="none" stroke={dim} strokeWidth="0.8" strokeDasharray="2 5" />
      <circle cx="160" cy="160" r="88" fill="none" stroke={dim} strokeWidth="0.6" strokeDasharray="1 6" />
      {nodes.map((n) => (
        <line key={n.label} x1={n.x} y1={n.y} x2="160" y2="160"
          stroke={n.active ? "rgba(201,164,92,0.5)" : dim} strokeWidth="0.9" />
      ))}
      <circle cx="160" cy="160" r="7" fill={gold}>
        <animate attributeName="opacity" values="1;0.55;1" dur="3s" repeatCount="indefinite" />
      </circle>
      <circle cx="160" cy="160" r="14" fill="none" stroke={gold} strokeWidth="0.7" opacity="0.6" />
      {nodes.map((n) => (
        <g key={n.label}>
          <circle cx={n.x} cy={n.y} r="5"
            fill={n.active ? gold : "none"}
            stroke={n.active ? gold : dim} strokeWidth="1.2" />
          <text x={n.x} y={n.y + (n.y > 160 ? 24 : n.y < 160 ? -14 : 26)}
            textAnchor="middle" fontSize="13" fill={n.active ? ink : dim}
            fontFamily="'Hiragino Sans', sans-serif">
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
