"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "@/lib/i18n";
import { motion } from "framer-motion";
import { useTranslations } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";

const LAYER_COLORS: Record<string, string> = {
  tools: "#3B82F6",
  planning: "#10B981",
  memory: "#8B5CF6",
  concurrency: "#F59E0B",
  collaboration: "#EF4444",
};

export function KnowledgeGraph() {
  const t = useTranslations("sessions");
  const homeT = useTranslations("home");
  const vizT = useTranslations("viz");
  const [hovered, setHovered] = useState<string | null>(null);

  const width = 760;
  const height = 360;

  // group nodes by layer and compute positions
  const nodes = useMemo(() => {
    const groups: Record<string, string[]> = {};
    LEARNING_PATH.forEach((id) => {
      const layer = VERSION_META[id]?.layer || "tools";
      groups[layer] = groups[layer] || [];
      groups[layer].push(id);
    });

    const rows = LAYERS.map((l, idx) => {
      const items = groups[l.id] || [];
      const y = 40 + idx * ((height - 80) / Math.max(1, LAYERS.length - 1));
      return items.map((id, i) => ({ id, layer: l.id, x: 100 + (items.length === 1 ? (width - 200) / 2 : (i / (items.length - 1)) * (width - 200)), y }));
    }).flat();

    return rows;
  }, [] as Array<{id:string,layer:string,x:number,y:number}>);

  const links = useMemo(() => LEARNING_PATH.slice(0, -1).map((id, idx) => ({ source: id, target: LEARNING_PATH[idx + 1] })), []);

  const router = useRouter();
  const locale = useLocale();

  function handleNodeClick(id: string) {
    // navigate to version page for the node
    router.push(`/${locale}/${id}`);
  }

  function renderShape(layer: string, widthPx: number, heightPx: number, fill: string, stroke: string) {
    const halfX = widthPx / 2;
    const halfY = heightPx / 2;
    const strokeProps = { stroke, strokeWidth: 1 };
    const transformStyle = { transformBox: 'fill-box', transformOrigin: '50% 50%' } as any;
    switch (layer) {
      case "planning":
        return <rect x={-halfX} y={-halfY} rx={8} ry={8} width={widthPx} height={heightPx} fill={fill} {...strokeProps} style={transformStyle} />;
      case "memory":
        return <ellipse cx={0} cy={0} rx={halfX} ry={halfY * 0.85} fill={fill} {...strokeProps} style={transformStyle} />;
      case "concurrency":
        return <polygon points={`${0},${-halfY} ${halfX},0 ${0},${halfY} ${-halfX},0`} fill={fill} {...strokeProps} style={transformStyle} />;
      case "collaboration":
        // hexagon using width/height
        return (
          <polygon
            points={`${-halfX * 0.85},${-halfY / 2} ${0},${-halfY} ${halfX * 0.85},${-halfY / 2} ${halfX * 0.85},${halfY / 2} ${0},${halfY} ${-halfX * 0.85},${halfY / 2}`}
            fill={fill}
            {...strokeProps}
            style={transformStyle}
          />
        );
      default:
        return <rect x={-halfX} y={-halfY} rx={8} ry={8} width={widthPx} height={heightPx} fill={fill} {...strokeProps} style={transformStyle} />;
    }
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{homeT("knowledge_graph_title") || "Knowledge Graph"}</h3>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{homeT("knowledge_graph_desc") || "Visual representation of the learning path aligned to architecture layers"}</p>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
        {links.map((l) => {
          const s = nodes.find(n => n.id === l.source);
          const tNode = nodes.find(n => n.id === l.target);
          if (!s || !tNode) return null;
          const cx = s.x + (tNode.x - s.x) / 2;
          const cy = s.y + (tNode.y - s.y) / 2 - 20;
          return (
            <path key={`${l.source}-${l.target}`} d={`M ${s.x} ${s.y} Q ${cx} ${cy} ${tNode.x} ${tNode.y}`} stroke={LAYER_COLORS[s.layer]} strokeWidth={1.4} fill="none" opacity={0.5} />
          );
        })}

        {nodes.map((n) => {
          const meta = VERSION_META[n.id];
          const label = vizT(n.id) || meta?.title || n.id;
          const isHovered = hovered === n.id;
          const strokeColor = isHovered ? "#fff" : "rgba(255,255,255,0.9)";
          const fill = LAYER_COLORS[n.layer] || "#64748b";
          const approxWidth = Math.min(220, Math.max(56, (label?.length || 6) * 7 + 24));
          const widthPx = isHovered ? Math.max(approxWidth, 96) : approxWidth;
          const heightPx = isHovered ? 40 : 32;
          return (
            <motion.g
              key={n.id}
              transform={`translate(${n.x}, ${n.y})`}
              className="cursor-pointer"
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleNodeClick(n.id)}
              role="button"
              aria-label={meta?.title || n.id}
              whileHover={{ scale: 1.06 }}
              style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
            >
              {renderShape(n.layer, widthPx, heightPx, fill, strokeColor)}
              <text x={0} y={4} textAnchor="middle" fontSize={10} fontWeight={600} fill="#fff">{label}</text>
              {isHovered && (
                <g transform={`translate(18, -34)`}> 
                  <rect x={0} y={0} width={220} height={56} rx={8} fill="var(--color-bg)" stroke="var(--color-border)" />
                  <text x={8} y={16} fontSize={12} fill="var(--color-text)" fontWeight={700}>{meta?.title}</text>
                  <text x={8} y={34} fontSize={10} fill="var(--color-text-secondary)">{meta?.subtitle}</text>
                </g>
              )}
            </motion.g>
          );
        })}
      </svg>

      <div className="mt-4 flex flex-wrap justify-center gap-4">
        {LAYERS.map(layer => (
          <div key={layer.id} className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: LAYER_COLORS[layer.id] }} />
            <span className="text-xs text-[var(--color-text-secondary)]">{homeT(`layers.${layer.id}.label`) || layer.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
