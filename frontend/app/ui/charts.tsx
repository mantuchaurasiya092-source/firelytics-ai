"use client";

import { useMemo, useState } from "react";
import {
  clamp,
  fmt,
  GravityPoint,
  HabitatMarker,
  HABITAT_SHORT,
  DigitalTwinPoint,
  MlMetricSet,
  MlShapSummary,
  rangeText,
  RunSummary,
  scale,
  Simulation,
  RankItem,
  TelemetryFrame,
} from "./model";

export type ChartTheme = "light" | "dark";

const CHART_COLORS = {
  light: {
    text: "#000000", muted: "#0f172a", grid: "#e5e7eb", axis: "#64748b", plot: "#ffffff", markerStroke: "#ffffff",
    cyan: "#06b6d4", cyanSoft: "#22d3ee", emerald: "#10b981", teal: "#14b8a6",
    amber: "#f59e0b", red: "#ef4444", orange: "#f97316", violet: "#8b5cf6", blue: "#3b82f6",
    phase0: "#047857", phase1: "#2563eb", active: "#ec4899",
    boxBg: "rgba(255,255,255,.92)", boxBorder: "#f59e0b", calloutBg: "rgba(245,158,11,.20)", onAccent: "#ffffff",
  },
  dark: {
    text: "#ffffff", muted: "#f8fafc", grid: "#27272a", axis: "#9ca3af", plot: "#0a0a0f", markerStroke: "#050505",
    cyan: "#06b6d4", cyanSoft: "#22d3ee", emerald: "#10b981", teal: "#14b8a6",
    amber: "#f59e0b", red: "#ef4444", orange: "#f97316", violet: "#8b5cf6", blue: "#3b82f6",
    phase0: "#047857", phase1: "#2563eb", active: "#22d3ee",
    boxBg: "rgba(10,10,14,.94)", boxBorder: "#f59e0b", calloutBg: "rgba(245,158,11,.20)", onAccent: "#ffffff",
  },
} as const;

type Tip = { x: number; y: number; title: string; lines: string[] };

type TelemetryTrack = {
  field: "temp_c" | "O2_pct" | "airflow_cms";
  title: string;
  unit: string;
  color: string;
  fallback: [number, number];
};

const TELEMETRY_TRACKS: TelemetryTrack[] = [
  { field: "temp_c", title: "TEMPERATURE", unit: "°C", color: "#ef4444", fallback: [0, 100] },
  { field: "O2_pct", title: "OXYGEN", unit: "%", color: "#06b6d4", fallback: [0, 30] },
  { field: "airflow_cms", title: "AIRFLOW", unit: "cm/s", color: "#10b981", fallback: [0, 20] },
];

type TelemetryHover = { xPct: number; yPct: number; title: string; value: string };

export function LiveTelemetryChart({
  history,
  theme,
}: {
  history: TelemetryFrame[];
  theme: ChartTheme;
}) {
  const [hovered, setHovered] = useState<TelemetryHover | null>(null);
  const C = CHART_COLORS[theme];
  const W = 900;
  const H = 464;
  const L = 90;
  const R = 24;
  const plotWidth = W - L - R;
  const trackHeight = 112;
  const trackGap = 28;
  const top = 26;
  const frames = history.slice(-60);
  const x = (index: number) => L + (index / Math.max(1, frames.length - 1)) * plotWidth;
  const tooltipStyle = {
    background: theme === "dark" ? "#0a0a0f" : "#ffffff",
    borderColor: theme === "dark" ? "#ffffff" : "#000000",
    color: theme === "dark" ? "#ffffff" : "#000000",
    left: `${Math.min(78, Math.max(1, hovered?.xPct ?? 1))}%`,
    top: `${Math.min(88, Math.max(2, hovered?.yPct ?? 2))}%`,
  };

  return (
    <div className="chart-shell telemetry-chart-shell">
      <div className="chart-plot telemetry-chart-plot">
        <svg
          className="chart-svg telemetry-chart-svg"
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height="auto"
          role="img"
          aria-label="Rolling telemetry time series for temperature, oxygen, and airflow"
        >
          {TELEMETRY_TRACKS.map((track, trackIndex) => {
            const yTop = top + trackIndex * (trackHeight + trackGap);
            const yBottom = yTop + trackHeight - 22;
            const values = frames.map((frame) => frame[track.field]);
            const finiteValues = values.filter(
              (value): value is number => typeof value === "number" && Number.isFinite(value),
            );
            let [minimum, maximum] = track.fallback;
            if (finiteValues.length) {
              const observedMin = Math.min(...finiteValues);
              const observedMax = Math.max(...finiteValues);
              const padding = observedMax === observedMin
                ? Math.max(Math.abs(observedMax) * 0.05, 1)
                : (observedMax - observedMin) * 0.12;
              minimum = observedMin - padding;
              maximum = observedMax + padding;
            }
            const y = (value: number) =>
              yBottom - ((value - minimum) / Math.max(Number.EPSILON, maximum - minimum)) * (yBottom - yTop);
            let drawing = false;
            const path = values.map((value, index) => {
              if (typeof value !== "number" || !Number.isFinite(value)) {
                drawing = false;
                return "";
              }
              const command = drawing ? "L" : "M";
              drawing = true;
              return `${command}${x(index).toFixed(2)},${y(value).toFixed(2)}`;
            }).join(" ");
            const ticks = [0, 0.5, 1].map((fraction) => minimum + fraction * (maximum - minimum));

            return (
              <g key={track.field}>
                <text x="12" y={yTop + 12} fill={C.text} fontSize="10" fontWeight="700">
                  {track.title} · {track.unit}
                </text>
                <text x={W - R} y={yTop + 12} fill={C.text} fontSize="9" textAnchor="end">
                  {finiteValues.length
                    ? `${Math.min(...finiteValues).toFixed(2)} – ${Math.max(...finiteValues).toFixed(2)} ${track.unit}`
                    : "NOT RECORDED"}
                </text>
                {ticks.map((tick, index) => {
                  const yPos = y(tick);
                  return (
                    <g key={`${track.field}-tick-${index}`}>
                      <line x1={L} x2={W - R} y1={yPos} y2={yPos} stroke="#334155" strokeDasharray="3 4" />
                      <text x={L - 8} y={yPos + 3} fill={C.text} fontSize="8" textAnchor="end">
                        {tick.toFixed(1)}
                      </text>
                    </g>
                  );
                })}
                {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
                  const xPos = L + fraction * plotWidth;
                  return (
                    <line
                      key={`${track.field}-x-${fraction}`}
                      x1={xPos}
                      x2={xPos}
                      y1={yTop + 18}
                      y2={yBottom}
                      stroke="#334155"
                      strokeDasharray="3 4"
                    />
                  );
                })}
                <line x1={L} x2={W - R} y1={yBottom} y2={yBottom} stroke={C.text} strokeWidth="0.8" />
                {path && <path d={path} fill="none" stroke={track.color} strokeWidth="2.5" strokeLinejoin="round" />}
                {values.map((value, index) => {
                  if (typeof value !== "number" || !Number.isFinite(value)) return null;
                  const pointX = x(index);
                  const pointY = y(value);
                  const timestamp = frames[index]?.source_timestamp ?? frames[index]?.timestamp ?? "timestamp unavailable";
                  const title = `${track.title} · frame ${frames[index]?.frame_id ?? index + 1}`;
                  const formatted = `${value.toFixed(3)} ${track.unit} · ${timestamp}`;
                  return (
                    <circle
                      key={`${track.field}-point-${frames[index]?.frame_id ?? index}`}
                      cx={pointX}
                      cy={pointY}
                      r="3"
                      fill={track.color}
                      stroke={theme === "dark" ? "#ffffff" : "#000000"}
                      strokeWidth="0.7"
                      tabIndex={0}
                      role="img"
                      aria-label={`${title}: ${formatted}`}
                      onMouseEnter={() => setHovered({
                        xPct: (pointX / W) * 100,
                        yPct: (pointY / H) * 100,
                        title,
                        value: formatted,
                      })}
                      onMouseLeave={() => setHovered(null)}
                      onFocus={() => setHovered({
                        xPct: (pointX / W) * 100,
                        yPct: (pointY / H) * 100,
                        title,
                        value: formatted,
                      })}
                      onBlur={() => setHovered(null)}
                    />
                  );
                })}
                {!finiteValues.length && (
                  <text
                    x={(L + W - R) / 2}
                    y={(yTop + yBottom) / 2}
                    fill={C.text}
                    fontSize="10"
                    textAnchor="middle"
                  >
                    No recorded {track.title.toLowerCase()} values in this source
                  </text>
                )}
              </g>
            );
          })}
          <text x={L} y={H - 12} fill={C.text} fontSize="8">OLDER FRAMES</text>
          <text x={W - R} y={H - 12} fill={C.text} fontSize="8" textAnchor="end">LATEST FRAME · 1 S POLL</text>
        </svg>
        {hovered && (
          <div className="telemetry-chart-tooltip" style={tooltipStyle} role="tooltip">
            <strong>{hovered.title}</strong>
            <span>{hovered.value}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function DigitalTwinComparisonChart({
  baseline,
  intervention,
  field,
  theme,
}: {
  baseline: DigitalTwinPoint[];
  intervention: DigitalTwinPoint[];
  field: "o2_pct" | "pressure_psi" | "airflow_cms" | "gravity_g";
  theme: ChartTheme;
}) {
  const C = CHART_COLORS[theme];
  const width = 900;
  const height = 340;
  const left = 76;
  const right = width - 28;
  const top = 50;
  const bottom = height - 52;
  const fieldLabel = {
    o2_pct: "OXYGEN",
    pressure_psi: "PRESSURE",
    airflow_cms: "AIRFLOW",
    gravity_g: "GRAVITY",
  }[field];
  const fieldUnit = {
    o2_pct: "%",
    pressure_psi: "psi",
    airflow_cms: "cm/s",
    gravity_g: "g",
  }[field];
  const points = [...baseline, ...intervention];
  const values = points.map((point) => point[field]).filter(Number.isFinite);
  const minValue = Math.min(0, ...values);
  const maxValue = Math.max(1, ...values);
  const maxTime = Math.max(1, ...points.map((point) => point.time));
  const x = (time: number) => left + (time / maxTime) * (right - left);
  const y = (value: number) => bottom - ((value - minValue) / (maxValue - minValue)) * (bottom - top);
  const pathFor = (series: DigitalTwinPoint[]) => series
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.time).toFixed(2)} ${y(point[field]).toFixed(2)}`)
    .join(" ");

  return (
    <div className="chart-shell digital-twin-chart-shell">
      <div className="chart-plot">
        <svg
          className="chart-svg digital-twin-chart-svg"
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height="auto"
          role="img"
          aria-label={`Exploratory ${fieldLabel} boundary-condition comparison for baseline and intervention scenarios`}
        >
          <text x={left} y="22" fill={C.text} fontSize="11" fontWeight="700">{fieldLabel} BOUNDARY CONDITION · {fieldUnit}</text>
          <line x1={left + 8} x2={left + 42} y1="38" y2="38" stroke="#ef4444" strokeWidth="3" strokeDasharray="7 4" />
          <text x={left + 48} y="41" fill={C.text} fontSize="9">BASELINE</text>
          <line x1={left + 152} x2={left + 186} y1="38" y2="38" stroke="#10b981" strokeWidth="3" />
          <text x={left + 192} y="41" fill={C.text} fontSize="9">INTERVENTION BOUNDARY</text>
          {[0, 0.5, 1].map((fraction) => {
            const value = minValue + fraction * (maxValue - minValue);
            const yPos = y(value);
            return (
              <g key={`o2-y-${fraction}`}>
                <line x1={left} x2={right} y1={yPos} y2={yPos} stroke={theme === "dark" ? "#334155" : "#cbd5e1"} strokeDasharray="3 4" />
                <text x={left - 10} y={yPos + 3} fill={C.text} fontSize="9" textAnchor="end">{value.toFixed(1)}</text>
              </g>
            );
          })}
          {[0, 0.5, 1].map((fraction) => {
            const time = fraction * maxTime;
            const xPos = x(time);
            return (
              <g key={`o2-x-${fraction}`}>
                <line x1={xPos} x2={xPos} y1={top} y2={bottom} stroke={theme === "dark" ? "#334155" : "#cbd5e1"} strokeDasharray="3 4" />
                <text x={xPos} y={bottom + 18} fill={C.text} fontSize="9" textAnchor="middle">{time.toFixed(1)}</text>
              </g>
            );
          })}
          <line x1={left} x2={right} y1={bottom} y2={bottom} stroke={C.text} />
          <line x1={left} x2={left} y1={top} y2={bottom} stroke={C.text} />
          <text x={(left + right) / 2} y={height - 12} fill={C.text} fontSize="9" textAnchor="middle">TIME · SECONDS</text>
          <path d={pathFor(baseline)} fill="none" stroke="#ef4444" strokeWidth="2.7" strokeDasharray="7 4" />
          <path d={pathFor(intervention)} fill="none" stroke="#10b981" strokeWidth="2.7" />
          {baseline.map((point, index) => (
            <circle key={`base-${index}`} cx={x(point.time)} cy={y(point[field])} r="2.4" fill="#ef4444">
              <title>Baseline · {point.time.toFixed(1)} s · {point[field].toFixed(2)} {fieldUnit}</title>
            </circle>
          ))}
          {intervention.map((point, index) => (
            <circle key={`intervention-${index}`} cx={x(point.time)} cy={y(point[field])} r="2.4" fill="#10b981">
              <title>Intervention boundary · {point.time.toFixed(1)} s · {point[field].toFixed(2)} {fieldUnit}</title>
            </circle>
          ))}
        </svg>
      </div>
    </div>
  );
}

function habitatColor(id: string, theme: ChartTheme): string {
  return ({
    iss_usos: "#10b981",
    artemis_lunar_base: "#eab308",
    mars_transit_habitat: "#38bdf8",
    eva_spacesuit: "#ef4444",
    high_o2_testbed: "#f97316",
    user_scenario: theme === "dark" ? "#22d3ee" : "#ec4899",
  } as Record<string, string>)[id] ?? CHART_COLORS[theme].muted;
}

function ChartTip({ tip, width, height, below }: { tip: Tip | null; width: number; height: number; below?: boolean }) {
  if (!tip) return null;
  const left = Math.min(Math.max(tip.x, 8), width - 258);
  return (
    <div
      className={`chart-tooltip ${(below ?? (tip.y < 103)) ? "below" : ""}`}
      style={{ left: `clamp(8px, ${(left / width) * 100}%, calc(100% - 258px))`, top: `${(tip.y / height) * 100}%` }}
      role="status"
    >
      <b>{tip.title}</b>
      {tip.lines.map((line, index) => <i key={`${line}-${index}`}>{line}</i>)}
    </div>
  );
}

function AxisGrid({
  xTicks, yTicks, x, y, x0, x1, y0, y1, xLabel, yLabel,
}: {
  xTicks: number[]; yTicks: number[]; x: (value: number) => number; y: (value: number) => number;
  x0: number; x1: number; y0: number; y1: number; xLabel: string; yLabel: string;
}) {
  return (
    <g>
      {yTicks.map((tick) => (
        <g key={`y-${tick}`}>
          <line className="grid-line" x1={x0} x2={x1} y1={y(tick)} y2={y(tick)} />
          <text className="tick-label" x={x0 - 8} y={y(tick) + 3} textAnchor="end">{tick}</text>
        </g>
      ))}
      {xTicks.map((tick) => (
        <g key={`x-${tick}`}>
          <line className="grid-line" x1={x(tick)} x2={x(tick)} y1={y0} y2={y1} />
          <text className="tick-label" x={x(tick)} y={y1 + 16} textAnchor="middle">{tick}</text>
        </g>
      ))}
      <line className="axis-line" x1={x0} x2={x1} y1={y1} y2={y1} />
      <line className="axis-line" x1={x0} x2={x0} y1={y0} y2={y1} />
      <text className="axis-title" x={(x0 + x1) / 2} y={y1 + 34} textAnchor="middle">{xLabel}</text>
      <text className="axis-title" transform={`translate(${x0 - 42},${(y0 + y1) / 2}) rotate(-90)`} textAnchor="middle">{yLabel}</text>
    </g>
  );
}

export function O2PressureEnvelopeChart({
  simulation, activeHabitat, onSelectHabitat, theme,
}: {
  simulation: Simulation; activeHabitat: string; onSelectHabitat: (id: string) => void; theme: ChartTheme;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const C = CHART_COLORS[theme];
  const W = 780;
  const H = 430;
  const L = 64;
  const R = 22;
  const T = 28;
  const B = 58;
  const x0 = L;
  const x1 = W - R;
  const y0 = T;
  const y1 = H - B;
  const x = (pressure: number) => scale(pressure, 0, 18, x0, x1);
  const y = (oxygen: number) => scale(oxygen, 10, 100, y1, y0);

  const boundary = useMemo(
    () => [...simulation.boundary_curve].sort((a, b) => a.pressure_psi - b.pressure_psi),
    [simulation.boundary_curve],
  );
  const curve = boundary.length
    ? boundary
    : [{ pressure_psi: 0, boundary_o2_pct: 16 }, { pressure_psi: 18, boundary_o2_pct: 17 }];
  const extended: [number, number][] = [
    [x(0), y(curve[0].boundary_o2_pct)],
    ...curve.map((point) => [x(point.pressure_psi), y(point.boundary_o2_pct)] as [number, number]),
    [x(18), y(curve[curve.length - 1].boundary_o2_pct)],
  ];
  const boundaryPath = extended.map(([px, py], index) => `${index === 0 ? "M" : "L"} ${px} ${py}`).join(" ");
  const flammablePath = `${boundaryPath} L ${x(18)} ${y(100)} L ${x(0)} ${y(100)} Z`;
  const safePath = `M ${x(0)} ${y(10)} L ${extended.map(([px, py]) => `${px} ${py}`).join(" L ")} L ${x(18)} ${y(10)} Z`;

  const normoxic = useMemo(() => {
    const points: [number, number][] = [];
    for (let pressure = 3.1; pressure <= 18.01; pressure += 0.2) {
      const oxygen = (3.087 / pressure) * 100;
      if (oxygen >= 10 && oxygen <= 100) points.push([x(pressure), y(oxygen)]);
    }
    return points.map(([px, py], index) => `${index === 0 ? "M" : "L"} ${px} ${py}`).join(" ");
  }, [x, y]);

  const active = simulation.habitat_markers.find((marker) => marker.id === activeHabitat);
  const moons = simulation.habitat_markers.filter((marker) => marker.id !== "user_scenario");
  const user = simulation.habitat_markers.find((marker) => marker.id === "user_scenario");
  const scatters = simulation.o2_pressure_envelope.slice(0, 45);
  const boundaryLabel = curve.reduce((nearest, point) =>
    Math.abs(point.pressure_psi - 7) < Math.abs(nearest.pressure_psi - 7) ? point : nearest, curve[0]);

  const hover = (marker: HabitatMarker) => setTip({
    x: x(marker.pressure_psi),
    y: y(marker.o2_pct),
    title: marker.label,
    lines: [
      `${fmt(marker.o2_pct, 1)}% O₂ · ${fmt(marker.pressure_psi, 1)} psi`,
      `P_O2 = ${fmt((marker.o2_pct / 100) * marker.pressure_psi, 2)} psi`,
      marker.screening_side_of_boundary.replaceAll("_", " "),
    ],
  });

  return (
    <div className="chart-shell">
      <div className="chart-plot">
        <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Oxygen concentration versus cabin pressure flammability envelope">
        <defs>
          <linearGradient id="flammable-zone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.red} stopOpacity="0.28" />
            <stop offset="100%" stopColor={C.orange} stopOpacity="0.14" />
          </linearGradient>
          <linearGradient id="safe-zone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.emerald} stopOpacity="0.08" />
            <stop offset="100%" stopColor={C.teal} stopOpacity="0.22" />
          </linearGradient>
        </defs>
        <path d={flammablePath} fill="url(#flammable-zone)" />
        <path d={safePath} fill="url(#safe-zone)" />
        {scatters.map((point, index) => (
          <circle
            key={`${point.pressure_psi}-${point.o2_pct}-${index}`}
            cx={x(point.pressure_psi)}
            cy={y(point.o2_pct)}
            r={1.6}
            fill={point.screening_side_of_boundary === "above_surrogate_moc" ? C.red : C.emerald}
            opacity={0.32}
          />
        ))}
        <AxisGrid
          xTicks={[0, 3, 6, 9, 12, 15, 18]}
          yTicks={[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]}
          x={x}
          y={y}
          x0={x0}
          x1={x1}
          y0={y0}
          y1={y1}
          xLabel="CABIN PRESSURE (psi) · 14.7 psi = 1 atm"
          yLabel="OXYGEN CONCENTRATION (%)"
        />
        <text className="annotation" x={x(2.1)} y={y(38)} fill={C.text} opacity={0.95}>SELF-EXTINGUISHING SAFE ZONE</text>
        <text className="annotation" x={x(8.4)} y={y(84)} fill={C.text} opacity={0.95}>FLAMMABLE PROPAGATION ZONE</text>
        <path d={normoxic} fill="none" stroke={C.cyan} strokeWidth={1.8} strokeDasharray="6 4" opacity={0.95} />
        <text className="series-label" x={x(8) + 8} y={y((3.087 / 8) * 100) - 7} fill={C.text}>NORMOXIC ISOBAR · P_O2 3.09 psi</text>
        <path d={boundaryPath} fill="none" stroke={C.amber} strokeWidth={3} />
        <text className="series-label" x={x(boundaryLabel.pressure_psi) + 8} y={y(boundaryLabel.boundary_o2_pct) + 14} fill={C.text}>BASS-II / SAFFIRE SCREENING BOUNDARY</text>
        {moons.map((marker) => {
          const color = habitatColor(marker.id, theme);
          const isActive = activeHabitat === marker.id;
          const labelOffset = ({
            eva_spacesuit: { dx: 10, dy: 4, anchor: "start" },
            artemis_lunar_base: { dx: -8, dy: -10, anchor: "end" },
            mars_transit_habitat: { dx: 10, dy: -10, anchor: "start" },
            iss_usos: { dx: 10, dy: -12, anchor: "start" },
            high_o2_testbed: { dx: 10, dy: 14, anchor: "start" },
          } as Record<string, { dx: number; dy: number; anchor: "start" | "end" }>)[marker.id]
            ?? { dx: 8, dy: -7, anchor: "start" as const };
          return (
            <g
              key={marker.id}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => hover(marker)}
              onMouseLeave={() => setTip(null)}
              onClick={() => onSelectHabitat(marker.id)}
            >
              <circle cx={x(marker.pressure_psi)} cy={y(marker.o2_pct)} r={13} fill="transparent" />
              {isActive && <circle className="pulse-ring" cx={x(marker.pressure_psi)} cy={y(marker.o2_pct)} r={9} fill="none" stroke={color} strokeWidth={1.8} opacity={0.75} />}
              <circle cx={x(marker.pressure_psi)} cy={y(marker.o2_pct)} r={4.6} fill={color} stroke={C.markerStroke} strokeWidth={1.4} />
              <text
                x={x(marker.pressure_psi) + labelOffset.dx}
                y={y(marker.o2_pct) + labelOffset.dy}
                textAnchor={labelOffset.anchor}
                fill={C.text}
                fontSize={8.5}
                fontWeight={isActive ? 700 : 500}
              >
                {HABITAT_SHORT[marker.id] ?? marker.id}
              </text>
            </g>
          );
        })}
        {user && (
          <g>
            <line x1={x(user.pressure_psi)} x2={x(user.pressure_psi)} y1={y0} y2={y1} stroke={C.active} strokeWidth={1} strokeDasharray="3 4" opacity={0.7} />
            <line x1={x0} x2={x1} y1={y(user.o2_pct)} y2={y(user.o2_pct)} stroke={C.active} strokeWidth={1} strokeDasharray="3 4" opacity={0.7} />
            <circle className="pulse-ring" cx={x(user.pressure_psi)} cy={y(user.o2_pct)} r={11} fill="none" stroke={C.active} strokeWidth={1.8} />
            <circle cx={x(user.pressure_psi)} cy={y(user.o2_pct)} r={5.2} fill={C.active} stroke={C.markerStroke} strokeWidth={1.4} />
            {(() => {
              const labelX = Math.max(x0 + 92, Math.min(x(user.pressure_psi) - 12, x1));
              const labelY = Math.min(y1 - 4, y(user.o2_pct) + 18);
              const background = C.boxBg;
              return (
                <g>
                  <rect x={labelX - 88} y={labelY - 10} width={88} height={14} rx={4} fill={background} />
                  <text x={labelX - 5} y={labelY} textAnchor="end" fill={C.text} fontSize={8.5} fontWeight={700}>ACTIVE SCENARIO</text>
                </g>
              );
            })()}
          </g>
        )}
        </svg>
        <ChartTip tip={tip} width={W} height={H} below={Boolean(tip && tip.y < T + 75)} />
      </div>
      <div className="chart-legend">
        <span><i className="swatch" style={{ background: C.red, border: `1px solid ${C.red}` }} />Flammable propagation</span>
        <span><i className="swatch" style={{ background: C.emerald, border: `1px solid ${C.emerald}` }} />Self-extinguishing</span>
        <span><i className="swatch line" style={{ background: C.amber }} />Screening boundary</span>
        <span><i className="swatch line" style={{ background: C.cyan }} />Normoxic isobar</span>
        <span><i className="swatch" style={{ background: C.active }} />Active scenario</span>
      </div>
      <div className="chart-foot">
        <span><b>Click any habitat marker</b> to load its atmosphere and re-run the simulation.</span>
        <span>Boundary is a transparent screening surrogate anchored to BASS-II / SAFFIRE evidence; it is not a NASA flammability limit.</span>
      </div>
    </div>
  );
}

export function PartialGravityBoundingChart({
  curve, efield, targetGravity, theme,
}: {
  curve: GravityPoint[]; efield: Simulation["efield_equivalence"]; targetGravity: number; theme: ChartTheme;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const C = CHART_COLORS[theme];
  const W = 780;
  const H = 430;
  const L = 64;
  const R = 64;
  const T = 32;
  const B = 60;
  const x0 = L;
  const x1 = W - R;
  const y0 = T;
  const y1 = H - B;
  const x = (gravity: number) => scale(gravity, 0, 1, x0, x1);
  const yMoc = (moc: number) => scale(moc, 14.5, 17, y1, y0);
  const maxSpread = Math.max(0.5, ...curve.map((point) => point.flame_spread_rate_mms)) * 1.18;
  const ySpread = (spread: number) => scale(spread, 0, maxSpread, y1, y0);
  const points = curve.length ? curve : [{ gravity_g: 0, moc_pct: 16, buoyant_flow_cms: 0, effective_velocity_cms: 0, oxygen_supply_index: 0, cooling_penalty_pct: 0, gravity_enhancement_pct: 0, flame_spread_rate_mms: 0, regime: "Unknown" }];
  const lunar = points.reduce((best, point) => Math.abs(point.gravity_g - 0.166) < Math.abs(best.gravity_g - 0.166) ? point : best, points[0]);
  const mocPath = points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.gravity_g)} ${yMoc(point.moc_pct)}`).join(" ");
  const spreadPath = points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.gravity_g)} ${ySpread(point.flame_spread_rate_mms)}`).join(" ");
  const mocArea = `M ${x(points[0].gravity_g)} ${y1} L ${points.map((point) => `${x(point.gravity_g)} ${yMoc(point.moc_pct)}`).join(" L ")} L ${x(points[points.length - 1].gravity_g)} ${y1} Z`;
  const barWidth = Math.min(30, (x1 - x0) / (points.length * 2.4));
  const boxWidth = 216;
  const boxX = x(0.166) + 14 + boxWidth > x1 ? x(0.166) - boxWidth - 14 : x(0.166) + 14;
  const active = points.reduce((best, point) => Math.abs(point.gravity_g - targetGravity) < Math.abs(best.gravity_g - targetGravity) ? point : best, points[0]);
  const peak = points.reduce((best, point) => point.flame_spread_rate_mms > best.flame_spread_rate_mms ? point : best, points[0]);

  return (
    <>
      <div className="chart-shell">
        <div className="chart-plot">
          <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Partial gravity minimum oxygen concentration and flame spread bounding curve">
          <defs>
            <linearGradient id="moc-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={C.cyan} stopOpacity="0.24" />
              <stop offset="100%" stopColor={C.cyan} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={mocArea} fill="url(#moc-fill)" />
          {points.map((point) => {
            const height = y1 - ySpread(point.flame_spread_rate_mms);
            return (
              <rect
                key={`bar-${point.gravity_g}`}
                x={x(point.gravity_g) - barWidth / 2}
                y={ySpread(point.flame_spread_rate_mms)}
                width={barWidth}
                height={Math.max(0, height)}
                fill={C.amber}
                opacity={0.22}
                onMouseEnter={() => setTip({
                  x: x(point.gravity_g),
                  y: ySpread(point.flame_spread_rate_mms),
                  title: `${fmt(point.gravity_g, 3)} g`,
                  lines: [`Spread rate ${fmt(point.flame_spread_rate_mms, 2)} mm/s`, `MOC ${fmt(point.moc_pct, 2)}%`, point.regime],
                })}
                onMouseLeave={() => setTip(null)}
              />
            );
          })}
          <path d={spreadPath} fill="none" stroke={C.orange} strokeWidth={2.5} strokeDasharray="6 4" />
          {points.map((point) => (
            <circle key={`spread-${point.gravity_g}`} cx={x(point.gravity_g)} cy={ySpread(point.flame_spread_rate_mms)} r={2.8}             fill={C.amber} stroke={C.markerStroke} strokeWidth={1} />
          ))}
          <AxisGrid
            xTicks={[0, 0.166, 0.376, 0.5, 0.75, 1]}
            yTicks={[14.5, 15, 15.5, 16, 16.5, 17]}
            x={x}
            y={yMoc}
            x0={x0}
            x1={x1}
            y0={y0}
            y1={y1}
            xLabel="GRAVITY LEVEL (g) · LUNAR 0.166 · MARS 0.376 · EARTH 1.0"
            yLabel="MINIMUM OXYGEN CONCENTRATION (%)"
          />
          {[0.166, 0.376].map((gravity) => (
            <line key={`guide-${gravity}`} x1={x(gravity)} x2={x(gravity)} y1={y0} y2={y1} stroke={C.axis} strokeWidth={1} strokeDasharray="4 5" />
          ))}
          <text className="muted-label" x={x(0.166)} y={y1 + 30} textAnchor="middle" fill={C.text}>LUNAR</text>
          <text className="muted-label" x={x(0.376)} y={y1 + 30} textAnchor="middle" fill={C.text}>MARS</text>
          <text className="muted-label" x={x(1)} y={y1 + 30} textAnchor="middle">EARTH</text>
          <text className="tick-label" x={x1 + 8} y={ySpread(maxSpread) + 3}>{fmt(maxSpread, 1)}</text>
          <text className="tick-label" x={x1 + 8} y={ySpread(maxSpread / 2) + 3}>{fmt(maxSpread / 2, 1)}</text>
          <text className="tick-label" x={x1 + 8} y={y1 + 3}>0</text>
          <text className="axis-title" transform={`translate(${x1 + 44},${(y0 + y1) / 2}) rotate(90)`} textAnchor="middle" fill={C.text}>SPREAD (mm/s)</text>
          <path d={mocPath} fill="none" stroke={C.cyan} strokeWidth={2.6} />
          {points.map((point) => (
            <g key={`point-${point.gravity_g}`} onMouseEnter={() => setTip({
              x: x(point.gravity_g),
              y: yMoc(point.moc_pct),
              title: `${fmt(point.gravity_g, 3)} g · ${point.regime}`,
              lines: [
                `MOC ${fmt(point.moc_pct, 2)}%`,
                `Buoyant V ${fmt(point.buoyant_flow_cms, 1)} cm/s`,
                `Effective V ${fmt(point.effective_velocity_cms, 1)} cm/s`,
                `Spread ${fmt(point.flame_spread_rate_mms, 2)} mm/s`,
              ],
            })} onMouseLeave={() => setTip(null)} style={{ cursor: "crosshair" }}>
              <circle cx={x(point.gravity_g)} cy={yMoc(point.moc_pct)} r={11} fill="transparent" />
              <circle cx={x(point.gravity_g)} cy={yMoc(point.moc_pct)} r={Math.abs(targetGravity - point.gravity_g) < 0.02 ? 5.4 : 3.8} fill={C.cyan} stroke={C.markerStroke} strokeWidth={1.3} />
            </g>
          ))}
          <circle className="pulse-ring" cx={x(lunar.gravity_g)} cy={yMoc(lunar.moc_pct)} r={11} fill="none" stroke={C.red} strokeWidth={1.8} />
          <circle cx={x(lunar.gravity_g)} cy={yMoc(lunar.moc_pct)} r={5.8} fill={C.red} stroke={C.markerStroke} strokeWidth={1.4} />
          <g>
            <rect x={boxX} y={y0 + 12} width={boxWidth} height={62} rx={4} fill={C.calloutBg} stroke={C.amber} strokeWidth={1.4} />
            <text className="annotation" x={boxX + 10} y={y0 + 28} fill={C.text} fontSize={8.5} fontWeight={700}>LUNAR FLAMMABILITY DIP · 0.166 g</text>
            <text className="muted-label" x={boxX + 10} y={y0 + 43}>MOC {fmt(lunar.moc_pct, 2)}% · V_b {fmt(lunar.buoyant_flow_cms, 1)} cm/s</text>
            <text className="muted-label" x={boxX + 10} y={y0 + 55}>Slow inflow feeds O₂ without 1g cooling.</text>
            <text className="muted-label" x={boxX + 10} y={y0 + 67}>Target for LUCI / FM2 measurement.</text>
          </g>
          <line x1={x(active.gravity_g)} x2={x(active.gravity_g)} y1={yMoc(active.moc_pct)} y2={y1} stroke={C.violet} strokeWidth={1.4} strokeDasharray="2 4" opacity={0.9} />
          <circle cx={x(active.gravity_g)} cy={y1 - 7} r={3.5} fill={C.violet} />
          <text className="muted-label" x={x(active.gravity_g)} y={y1 - 14} textAnchor="middle" fill={C.text}>ACTIVE</text>
          </svg>
          <ChartTip tip={tip} width={W} height={H} below={Boolean(tip && tip.y < T + 75)} />
        </div>
        <div className="chart-legend">
          <span><i className="swatch line" style={{ background: C.cyan }} />MOC %</span>
          <span><i className="swatch line" style={{ background: C.orange }} />Flame spread mm/s</span>
          <span><i className="swatch" style={{ background: C.violet }} />Active gravity</span>
        </div>
      </div>
      <div className="badge-row">
        <div className="science-badge efield">
          <span>PSI-22 · ACME E-FIELD EQUIVALENT</span>
          <b>{fmt(efield.equivalent_voltage_kv, 2)} kV ≈ {fmt(efield.estimated_equivalent_kv_cm, 2)} kV/cm</b>
          <span>Matches V_b {fmt(efield.ion_velocity_match_cms, 1)} cm/s in 0 g · gap {fmt(efield.electrode_gap_cm, 2)} cm</span>
        </div>
        <div className="science-badge warn">
          <span>LUCI / FM2 · PLANNED LUNAR TARGET</span>
          <b>0.166 g · MOC {fmt(lunar.moc_pct, 2)}%</b>
          <span>Hypothesis awaiting direct lunar-gravity measurement</span>
        </div>
        <div className="science-badge alert">
          <span>PEAK HAZARD GRAVITY</span>
          <b>{fmt(peak.moc_pct, 2)}% MOC at {fmt(peak.gravity_g, 3)} g</b>
          <span>{peak.regime} · screening curve maximum</span>
        </div>
      </div>
    </>
  );
}

const FACTOR_LABELS: Record<string, string> = {
  "Research pillar": "Pillar",
  "Material / fuel": "Material",
  "Oxygen concentration": "O₂",
  Pressure: "Pressure",
  Airflow: "Flow",
  "Gravity regime": "Gravity",
};

function factorState(score: number | null): { className: string; icon: string; label: string } {
  if (score === 1) return { className: "match", icon: "✓", label: "match" };
  if (score === 0.5) return { className: "partial", icon: "~", label: "partial" };
  if (score === 0) return { className: "miss", icon: "×", label: "miss" };
  return { className: "unknown", icon: "—", label: "unknown" };
}

function MetricTrack({ label, value, tone }: { label: string; value: number; tone: "match" | "coverage" | "proximity" }) {
  const safe = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div className="metric-track">
      <span>{label}</span>
      <div className="metric-track-bar" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(safe)}>
        <i className={tone} style={{ width: `${safe}%` }} />
      </div>
      <b>{fmt(safe, 0)}%</b>
    </div>
  );
}

export function EvidenceBarChart({ ranked }: { ranked: RankItem[] }) {
  const rows = ranked.slice(0, 5);
  const proximity = (study: RankItem) => study.physics_proximity?.mean_overlap != null
    ? study.physics_proximity.mean_overlap * 100
    : null;

  if (!rows.length) return <div className="empty">Run a simulation to populate the ranking breakdown.</div>;

  return (
    <div className="chartc-wrap">
      <div className="chartc-key" aria-label="Factor match key">
        {Object.entries(FACTOR_LABELS).map(([factor, label]) => (
          <span key={factor}><i />{label}</span>
        ))}
        <span className="chartc-key-note">✓ match · ~ partial · × miss · — unknown</span>
      </div>

      {rows.map((study, index) => {
        const prox = proximity(study);
        return (
          <article className="chartc-row" key={study.psi_id}>
            <div className="chartc-left">
              <span className="chartc-rank">{String(index + 1).padStart(2, "0")}</span>
              <div className="chartc-identity">
                <h4>{study.short_name}</h4>
                <div className="chartc-idline"><span className="chartc-psi">{study.psi_id}</span><span>{study.hardware_rack}</span></div>
                <p>{study.pillars.join(" · ")}</p>
              </div>
            </div>

            <div className="chartc-center">
              <div className="factor-strip" role="list" aria-label={`${study.short_name} factor match strip`}>
                {(study.ranking_factors ?? []).map((factor) => {
                  const state = factorState(factor.score);
                  return (
                    <span
                      key={`${study.psi_id}-${factor.factor}`}
                      className={`factor-seg ${state.className}`}
                      role="listitem"
                      title={`${factor.factor} · ${factor.status} · score ${factor.score ?? "unknown"} — ${factor.explanation}`}
                    >
                      <b>{FACTOR_LABELS[factor.factor] ?? factor.factor}</b>
                      <em aria-label={state.label}>{state.icon}</em>
                    </span>
                  );
                })}
              </div>
              <div className="metric-tracks">
                <MetricTrack label="Match score" value={study.match_score} tone="match" />
                <MetricTrack label="Resolved coverage" value={study.evidence_coverage} tone="coverage" />
                <MetricTrack label="Physics proximity" value={prox ?? 0} tone="proximity" />
              </div>
            </div>

            <div className="chartc-readout">
              <b>{fmt(study.match_score, 1)}% <span>Match</span></b>
              <small>Coverage: {fmt(study.evidence_coverage, 0)}% · Proximity: {prox == null ? "—" : `${fmt(prox, 0)}%`}</small>
            </div>
          </article>
        );
      })}

      <p className="chartc-note">The factor strip shows documented evidence status, not a safety verdict. Unknown factors stay outside the score denominator. Hover any factor for its source reasoning.</p>
    </div>
  );
}

export function SamerTelemetryVisual({ summary, runId, theme }: { summary: RunSummary; runId: string; theme: ChartTheme }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const C = CHART_COLORS[theme];
  const phase = summary.phase_summary ?? {};
  const metrics = summary.periodicity_metrics ?? {};
  const first = Number(phase.FirstCycle ?? metrics.FirstEligibleCycle ?? 0);
  const last = Number(phase.LastCycle ?? metrics.LastEligibleCycle ?? 1);
  const phase0 = Number(phase.Phase0CycleCount ?? 0);
  const phase1 = Number(phase.Phase1CycleCount ?? 0);
  const total = Math.max(1, phase0 + phase1);
  const exceptions = (summary.exception_cycles ?? []).filter((cycle) => Number.isFinite(cycle));
  const mixed = (summary.mixed_cycle_ids ?? []).filter((cycle) => Number.isFinite(cycle));
  const blocks = summary.block_events ?? [];
  const lagRows = (summary.lag_correlations ?? [])
    .map((row) => ({ lag: Number(row.Lag), pairs: Number(row.ValidCyclePairs), value: Number(row.Autocorrelation) }))
    .filter((row) => Number.isFinite(row.lag) && Number.isFinite(row.value))
    .sort((a, b) => a.lag - b.lag);

  const W = 920;
  const H = 330;
  const L = 160;
  const R = 28;
  const stripX = (cycle: number) => scale(cycle, first, Math.max(first + 1, last), L, W - R);
  const barMax = W - R - L;
  const phaseBarL = 300;
  const phaseBarMax = W - R - phaseBarL;
  const lagW = 920;
  const lagH = 250;
  const lagL = 62;
  const lagR = 24;
  const lagT = 24;
  const lagB = 44;
  const lagMax = lagRows.length ? Math.max(...lagRows.map((row) => row.lag)) : 1;
  const lagMin = lagRows.length ? Math.min(...lagRows.map((row) => row.lag)) : 0;
  const lagX = (lag: number) => scale(lag, lagMin, lagMax, lagL, lagW - lagR);
  const lagY = (value: number) => scale(value, -0.4, 1, lagH - lagB, lagT);
  const lagPath = lagRows.map((row, index) => `${index === 0 ? "M" : "L"} ${lagX(row.lag)} ${lagY(row.value)}`).join(" ");

  return (
    <>
      <div className="chart-shell">
        <div className="chart-plot">
          <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" preserveAspectRatio="xMidYMid meet" role="img" aria-label={`SAME-R run ${runId} phase band agreement and exception cycle positions`}>
          <text x={12} y={22} fill={C.text} fontSize={10} fontWeight={700}>RUN {runId} · PHASE BAND AGREEMENT</text>
          <text x={12} y={51} fill={C.text} fontSize={9} fontWeight={700}>Phase 0 · Band {phase.Phase0DominantBand ?? "not recorded"}</text>
          <rect className="phase-bar" x={phaseBarL} y={36} width={phaseBarMax * (phase0 / total)} height={22} rx={3} fill={C.phase0} opacity={0.9} />
          <text className="phase-bar-label" x={phaseBarL + 8} y={51} fill={C.onAccent} fontSize={9} fontWeight={700}>{phase0.toLocaleString()} cycles</text>
          <text x={12} y={87} fill={C.text} fontSize={9} fontWeight={700}>Phase 1 · Band {phase.Phase1DominantBand ?? "not recorded"}</text>
          <rect className="phase-bar" x={phaseBarL} y={72} width={phaseBarMax * (phase1 / total)} height={22} rx={3} fill={C.phase1} opacity={0.9} />
          <text className="phase-bar-label" x={phaseBarL + 8} y={87} fill={C.onAccent} fontSize={9} fontWeight={700}>{phase1.toLocaleString()} cycles</text>
          <text x={W - R} y={51} textAnchor="end" className="muted-label">{(phase.ClassifiedCycles ?? "—")} classified</text>
          <text x={W - R} y={87} textAnchor="end" className="muted-label">{(phase.ExceptionCycles ?? "—")} phase exceptions</text>

          <text x={12} y={140} fill={C.text} fontSize={10} fontWeight={700}>EXCEPTION CYCLE POSITION</text>
          <text x={L} y={160} className="muted-label">{first.toLocaleString()}</text>
          <text x={W - R} y={160} textAnchor="end" className="muted-label">{last.toLocaleString()}</text>
          {blocks.slice(0, 60).map((block, index) => {
            const start = Number(block.StartCycle);
            const end = Number(block.EndCycle);
            if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
            const x1 = stripX(Math.min(start, end));
            const x2 = stripX(Math.max(start, end));
            return <rect key={`block-${index}`} x={x1} y={168} width={Math.max(1, x2 - x1)} height={10} rx={2} fill={C.amber} opacity={0.18} />;
          })}
          <line x1={L} x2={W - R} y1={190} y2={190} stroke={C.axis} strokeWidth={1} />
          {exceptions.slice(0, 600).map((cycle) => (
            <line
              key={`exception-${cycle}`}
              x1={stripX(cycle)}
              x2={stripX(cycle)}
              y1={182}
              y2={200}
              stroke={C.orange}
              strokeWidth={1.2}
              opacity={0.85}
              onMouseEnter={() => setTip({ x: stripX(cycle), y: 190, title: `Cycle ${cycle}`, lines: ["Archived phase exception", "Classification mismatch — not a fire or alarm"] })}
              onMouseLeave={() => setTip(null)}
            />
          ))}
          {mixed.slice(0, 200).map((cycle) => (
            <circle key={`mixed-${cycle}`} cx={stripX(cycle)} cy={206} r={2.2} fill={C.red} opacity={0.95} />
          ))}
          {lagRows.map((row) => {
            const px = scale(row.lag, lagMin, lagMax, 168, W - R);
            const py = scale(row.value, -0.4, 1, 300, 266);
            return <line key={`lag-stem-${row.lag}`} x1={px} x2={px} y1={scale(0, -0.4, 1, 300, 266)} y2={py} stroke={C.cyan} strokeWidth={1} opacity={0.45} />;
          })}
          <text x={L} y={224} className="muted-label">{exceptions.length} exception cycles · {mixed.length} mixed-band cycles · {blocks.length} block events</text>
          <text x={12} y={252} fill={C.text} fontSize={10} fontWeight={700}>ARCHIVED AUTOCORRELATION</text>
          {lagRows.length > 0 && (
            <>
              {[1, 0.5, 0, -0.5].map((tick) => (
                <g key={`lag-grid-${tick}`}>
                  <line className="grid-line" x1={160} x2={W - R} y1={scale(tick, -0.4, 1, 300, 266)} y2={scale(tick, -0.4, 1, 300, 266)} />
                  <text x={152} y={scale(tick, -0.4, 1, 300, 266) + 3} textAnchor="end" className="tick-label">{tick}</text>
                </g>
              ))}
              {lagRows.map((row) => (
                <circle
                  key={`lag-${row.lag}`}
                  cx={scale(row.lag, lagMin, lagMax, 168, W - R)}
                  cy={scale(row.value, -0.4, 1, 300, 266)}
                  r={1.8}
                  fill={C.cyan}
                  opacity={0.8}
                  onMouseEnter={() => setTip({
                    x: scale(row.lag, lagMin, lagMax, 168, W - R),
                    y: scale(row.value, -0.4, 1, 300, 266),
                    title: `Lag ${row.lag} cycles`,
                    lines: [`Autocorrelation ${fmt(row.value, 4)}`, `${row.pairs} valid cycle pairs`],
                  })}
                  onMouseLeave={() => setTip(null)}
                />
              ))}
              <text x={W - R} y={296} textAnchor="end" className="muted-label">lag 1 → {lagMax} cycles</text>
            </>
          )}
          {lagRows.length === 0 && <text x={L} y={292} className="muted-label">No archived lag rows are available for this run.</text>}
          </svg>
          <ChartTip tip={tip} width={W} height={H} />
        </div>
        <div className="chart-legend">
          <span><i className="swatch" style={{ background: C.amber }} />Phase exception</span>
          <span><i className="swatch" style={{ background: C.red }} />Mixed-band cycle</span>
          <span><i className="swatch" style={{ background: C.violet, opacity: .35 }} />Block event span</span>
          <span><i className="swatch" style={{ background: C.cyan }} />Lag autocorrelation</span>
        </div>
      </div>

      <div className="chart-shell" style={{ marginTop: 10 }}>
        <div className="chart-plot">
          <svg className="chart-svg" viewBox={`0 0 ${lagW} ${lagH}`} width="100%" height="auto" preserveAspectRatio="xMidYMid meet" role="img" aria-label="SAME-R lag autocorrelation curve">
          <AxisGrid
            xTicks={[lagMin, Math.round((lagMin + lagMax) / 2), lagMax]}
            yTicks={[-0.4, 0, 0.5, 1]}
            x={lagX}
            y={lagY}
            x0={lagL}
            x1={lagW - lagR}
            y0={lagT}
            y1={lagH - lagB}
            xLabel="LAG (CYCLES)"
            yLabel="AUTOCORRELATION"
          />
          <line x1={lagL} x2={lagW - lagR} y1={lagY(0)} y2={lagY(0)} stroke={C.axis} strokeWidth={1} strokeDasharray="3 4" />
          {lagRows.map((row) => (
            <line key={`lag-stem-${row.lag}`} x1={lagX(row.lag)} x2={lagX(row.lag)} y1={lagY(0)} y2={lagY(row.value)} stroke={C.cyan} strokeWidth={1.2} opacity={0.5} />
          ))}
          <path d={lagPath} fill="none" stroke={C.cyan} strokeWidth={1.8} />
          {lagRows.map((row) => (
            <circle
              key={`lagdot-${row.lag}`}
              cx={lagX(row.lag)}
              cy={lagY(row.value)}
              r={3}
              fill={C.cyanSoft}
              stroke={C.markerStroke}
              strokeWidth={1}
              onMouseEnter={() => setTip({ x: lagX(row.lag), y: lagY(row.value), title: `Lag ${row.lag} cycles`, lines: [`r = ${fmt(row.value, 4)}`, `${row.pairs} valid pairs`] })}
              onMouseLeave={() => setTip(null)}
            />
          ))}
          <text x={lagL + 8} y={lagT + 12} className="muted-label">Archived 2026-11-14 analysis · not recomputed in this deployment</text>
          </svg>
          <ChartTip tip={tip} width={lagW} height={lagH} />
        </div>
      </div>
    </>
  );
}

export function DustDiscriminationPanel({ theme }: { theme: ChartTheme }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const C = CHART_COLORS[theme];
  const W = 620;
  const H = 170;
  const L = 42;
  const R = 18;
  const T = 26;
  const B = 42;
  const logMin = Math.log10(0.05);
  const logMax = Math.log10(5);
  const x = (diameter: number) => L + ((Math.log10(diameter) - logMin) / (logMax - logMin)) * (W - L - R);
  const y = H - B;
  const barHeight = 52;
  const smokeLabel = C.text;
  const dustLabel = C.text;
  return (
    <div className="chart-shell">
      <div className="chart-plot">
        <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Pyrolysis smoke versus cabin dust particle size discrimination">
        <text x={L} y={16} fill={C.text} fontSize={8.5} fontWeight={700}>SAME-R / DAFT PARTICLE-SIZE DISCRIMINATION</text>
        <rect x={x(0.1)} y={T} width={x(0.5) - x(0.1)} height={barHeight} fill={C.emerald} fillOpacity={0.25} stroke={C.emerald} strokeWidth={1.5} rx={3} />
        <rect x={x(1)} y={T} width={x(5) - x(1)} height={barHeight} fill={C.amber} fillOpacity={0.25} stroke={C.amber} strokeWidth={1.5} rx={3} />
        <text x={(x(0.1) + x(0.5)) / 2} y={T + 17} textAnchor="middle" fill={smokeLabel} fontSize={7} fontWeight={700}>
          <tspan x={(x(0.1) + x(0.5)) / 2}>PYROLYSIS SMOKE</tspan>
          <tspan x={(x(0.1) + x(0.5)) / 2} dy={10}>0.1–0.5 µm</tspan>
        </text>
        <text x={(x(1) + x(5)) / 2} y={T + 17} textAnchor="middle" fill={dustLabel} fontSize={7} fontWeight={700}>
          <tspan x={(x(1) + x(5)) / 2}>NUISANCE CABIN / LUNAR DUST</tspan>
          <tspan x={(x(1) + x(5)) / 2} dy={10}>&gt;1.0 µm</tspan>
        </text>
        <line x1={L} x2={W - R} y1={y} y2={y} stroke={C.axis} />
        {[0.1, 0.5, 1, 2, 5].map((tick) => (
          <g key={`size-${tick}`}>
            <line className="grid-line" x1={x(tick)} x2={x(tick)} y1={T} y2={y} />
            <text className="tick-label" x={x(tick)} y={y + 15} textAnchor="middle">{tick}</text>
          </g>
        ))}
        <text className="axis-title" x={W / 2} y={H - 6} textAnchor="middle">PARTICLE DIAMETER (µm, LOG SCALE)</text>
        <circle
          cx={x(0.3)}
          cy={T + 43}
          r={7}
          fill={C.emerald}
          stroke={C.markerStroke}
          strokeWidth={1.2}
          onMouseEnter={() => setTip({ x: x(0.3), y: T + 43, title: "SAME / SAME-R pyrolysis smoke", lines: ["D32 ≈ 0.1–0.5 µm", "Liquid aerosol; low-gravity coagulation", "PSI-101 / PSI-102"] })}
          onMouseLeave={() => setTip(null)}
        />
        <circle
          cx={x(2)}
          cy={T + 43}
          r={7}
          fill={C.amber}
          stroke={C.markerStroke}
          strokeWidth={1.2}
          onMouseEnter={() => setTip({ x: x(2), y: T + 43, title: "DAFT Arizona Road Dust", lines: ["> 1.0 µm mineral/cabin dust", "Nuisance aerosol standard", "PSI-47 · DustTrak / P-Trak"] })}
          onMouseLeave={() => setTip(null)}
        />
        </svg>
        <ChartTip tip={tip} width={W} height={H} />
      </div>
      <div className="chart-foot">
        <span><b>Operational reading:</b> size and number-density separation supports nuisance-alarm rejection for Artemis II-class telemetry. It is a screening hypothesis, not a qualified detector algorithm.</span>
      </div>
    </div>
  );
}

export function MlConfusionRocChart({
  metrics,
  theme,
}: {
  metrics: MlMetricSet;
  theme: ChartTheme;
}) {
  const C = CHART_COLORS[theme];
  const matrix = metrics.confusion_matrix.matrix;
  const maximum = Math.max(1, ...matrix.flat());
  const cellSize = 68;
  const xStart = 86;
  const yStart = 42;
  const colors = [[C.emerald, C.amber], [C.red, C.cyan]];
  const rocWidth = 340;
  const rocHeight = 250;
  const left = 44;
  const right = rocWidth - 14;
  const top = 20;
  const bottom = rocHeight - 42;
  const x = (value: number) => left + value * (right - left);
  const y = (value: number) => bottom - value * (bottom - top);
  const rocPath = metrics.roc_curve
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.false_positive_rate)} ${y(point.true_positive_rate)}`)
    .join(" ");

  return (
    <div className="ml-evaluation-charts">
      <div className="chart-shell">
        <div className="chart-plot">
          <svg
            className="chart-svg"
            viewBox="0 0 270 218"
            width="100%"
            height="auto"
            role="img"
            aria-label="Held-out-run confusion matrix for archived observed band classes"
          >
            <text x="12" y="18" fill={C.text} fontSize="10" fontWeight="700">GROUPED HELD-OUT CONFUSION MATRIX</text>
            <text x="13" y="89" fill={C.text} fontSize="8" transform="rotate(-90 13 89)" textAnchor="middle">ACTUAL CLASS</text>
            <text x="154" y="207" fill={C.text} fontSize="8" textAnchor="middle">PREDICTED CLASS</text>
            <text x={xStart + cellSize / 2} y="35" fill={C.text} fontSize="8" textAnchor="middle">10k–15k</text>
            <text x={xStart + cellSize * 1.5} y="35" fill={C.text} fontSize="8" textAnchor="middle">20k+</text>
            <text x="80" y={yStart + cellSize / 2 + 3} fill={C.text} fontSize="8" textAnchor="end">10k–15k</text>
            <text x="80" y={yStart + cellSize * 1.5 + 3} fill={C.text} fontSize="8" textAnchor="end">20k+</text>
            {matrix.map((row, rowIndex) => row.map((value, columnIndex) => (
              <g key={`cm-${rowIndex}-${columnIndex}`}>
                <rect
                  x={xStart + columnIndex * cellSize}
                  y={yStart + rowIndex * cellSize}
                  width={cellSize - 3}
                  height={cellSize - 3}
                  rx="4"
                  fill={colors[rowIndex][columnIndex]}
                  fillOpacity={0.18 + 0.58 * value / maximum}
                  stroke={colors[rowIndex][columnIndex]}
                />
                <text
                  x={xStart + columnIndex * cellSize + (cellSize - 3) / 2}
                  y={yStart + rowIndex * cellSize + cellSize / 2 + 4}
                  fill={C.text}
                  fontSize="14"
                  fontWeight="700"
                  textAnchor="middle"
                >
                  {value.toLocaleString()}
                </text>
              </g>
            )))}
            <text x="12" y="202" fill={C.muted} fontSize="7.5">
              Rows are held out by entire RunID; counts are out-of-fold.
            </text>
          </svg>
        </div>
      </div>
      <div className="chart-shell">
        <div className="chart-plot">
          <svg
            className="chart-svg"
            viewBox={`0 0 ${rocWidth} ${rocHeight}`}
            width="100%"
            height="auto"
            role="img"
            aria-label={`Leave-one-run-out ROC curve, AUC ${fmt(metrics.roc_auc, 3)}`}
          >
            <text x={left} y="12" fill={C.text} fontSize="10" fontWeight="700">LEAVE-ONE-RUN-OUT ROC</text>
            {[0, 0.5, 1].map((tick) => (
              <g key={`roc-${tick}`}>
                <line x1={x(tick)} x2={x(tick)} y1={top} y2={bottom} stroke={C.grid} />
                <line x1={left} x2={right} y1={y(tick)} y2={y(tick)} stroke={C.grid} />
                <text x={x(tick)} y={bottom + 15} fill={C.text} fontSize="8" textAnchor="middle">{tick.toFixed(1)}</text>
                <text x={left - 7} y={y(tick) + 3} fill={C.text} fontSize="8" textAnchor="end">{tick.toFixed(1)}</text>
              </g>
            ))}
            <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke={C.axis} strokeDasharray="4 4" />
            {rocPath && <path d={rocPath} fill="none" stroke={C.cyan} strokeWidth="2.5" />}
            <line x1={left} x2={right} y1={bottom} y2={bottom} stroke={C.text} />
            <line x1={left} x2={left} y1={top} y2={bottom} stroke={C.text} />
            <text x={(left + right) / 2} y={rocHeight - 7} fill={C.text} fontSize="8" textAnchor="middle">FALSE POSITIVE RATE</text>
            <text x="10" y={(top + bottom) / 2} fill={C.text} fontSize="8" textAnchor="middle" transform={`rotate(-90 10 ${(top + bottom) / 2})`}>TRUE POSITIVE RATE</text>
            <text x={right - 3} y={top + 12} fill={C.text} fontSize="9" textAnchor="end">AUC {fmt(metrics.roc_auc, 3)}</text>
          </svg>
        </div>
      </div>
    </div>
  );
}

export function MlShapFeatureChart({
  items,
  theme,
}: {
  items: MlShapSummary[];
  theme: ChartTheme;
}) {
  const C = CHART_COLORS[theme];
  const shown = [...items].sort((a, b) => a.rank - b.rank).slice(0, 5);
  const maxValue = Math.max(1e-12, ...shown.map((item) => item.mean_abs_shap));
  const width = 720;
  const labelWidth = 224;
  const plotWidth = width - labelWidth - 86;
  const rowHeight = 34;
  const height = 56 + shown.length * rowHeight;

  return (
    <div className="chart-shell">
      <div className="chart-plot">
        <svg
          className="chart-svg"
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height="auto"
          role="img"
          aria-label="Top five global exact Shapley feature contributions"
        >
          <defs>
            <linearGradient id="ml-shap-gradient" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor={C.emerald} />
              <stop offset="100%" stopColor={C.blue} />
            </linearGradient>
          </defs>
          <text x={labelWidth} y="17" fill={C.text} fontSize="9" fontWeight="700">
            MEAN ABSOLUTE SHAPLEY CONTRIBUTION TO P(OBSERVED BAND = 20K+)
          </text>
          {shown.map((item, index) => {
            const y = 34 + index * rowHeight;
            const barWidth = (item.mean_abs_shap / maxValue) * plotWidth;
            return (
              <g key={item.feature}>
                <text x={labelWidth - 9} y={y + 13} fill={C.text} fontSize="9" textAnchor="end">
                  {item.label}
                </text>
                <rect
                  x={labelWidth}
                  y={y}
                  width={Math.max(1, barWidth)}
                  height="20"
                  rx="4"
                  fill="url(#ml-shap-gradient)"
                />
                <text
                  x={labelWidth + Math.max(1, barWidth) + 6}
                  y={y + 14}
                  fill={C.text}
                  fontSize="8"
                >
                  {fmt(item.mean_abs_shap, 5)} · {item.unit}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="chart-foot">
        Exact empirical interventional Shapley values; descriptive of the training rows, not causal effects.
      </div>
    </div>
  );
}
