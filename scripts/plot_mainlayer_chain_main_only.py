"""Export a main-chain-only HTML view and one PNG for each k=3 cluster."""

from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.patches import FancyArrowPatch, Polygon


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data_clean" / "value_type" / "mainlayer_chain_clusters.json"
FIGS_DIR = PROJECT_ROOT / "figs" / "mainlayer"
HTML_OUTPUT = FIGS_DIR / "mainlayer_chain_clusters_main_only.html"
PNG_PATTERN = "mainlayer_chain_cluster_{cluster}_main_only.png"

SLOT_ORDER = ["S0", "S1", "S2", "S3"]
SLOT_DISPLAY = {
    "S0": "佳皆",
    "S1": "麻韵",
    "S2": "歌韵",
    "S3": "模韵",
}
SLOT_COLORS = {
    "S0": "#3366CC",
    "S1": "#F39C3D",
    "S2": "#55B86A",
    "S3": "#E778B4",
}


def set_font() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    for name in ["Arial Unicode MS", "PingFang HK", "Heiti TC", "Songti SC"]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_clusters() -> list[dict]:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    points = {point["point_id"]: point for point in payload["points"]}
    clusters = []
    for cluster in payload["solutions"]["3"]["clusters"]:
        item = dict(cluster)
        item["point"] = points[cluster["medoid_id"]]
        clusters.append(item)
    return clusters


def grouped_stops(slots: list[dict]) -> list[dict]:
    stops: list[dict] = []
    for slot in slots:
        if stops and abs(stops[-1]["x"] - slot["x"]) < 1e-9 and abs(stops[-1]["y"] - slot["y"]) < 1e-9:
            stops[-1]["slots"].append(slot)
        else:
            stops.append({"x": slot["x"], "y": slot["y"], "slots": [slot]})
    return stops


def stop_label(stop: dict) -> str:
    groups: list[dict] = []
    for slot in stop["slots"]:
        if groups and groups[-1]["value"] == slot["value"]:
            groups[-1]["names"].append(SLOT_DISPLAY[slot["slot"]])
        else:
            groups.append({"value": slot["value"], "names": [SLOT_DISPLAY[slot["slot"]]]})
    return " → ".join(f"{'–'.join(group['names'])} {group['value']}" for group in groups)


def display_chain(point: dict) -> str:
    return " → ".join(stop_label(stop) for stop in grouped_stops(point["slots"]))


def display_type_label(label: str) -> str:
    for slot in SLOT_ORDER:
        label = label.replace(slot, SLOT_DISPLAY[slot])
    return label


def draw_frame(ax: plt.Axes) -> None:
    frame = [(0, 0), (3, 0), (3, 3), (1.05, 3)]
    ax.add_patch(Polygon(frame, closed=True, fill=False, edgecolor="#d3d5d8", linewidth=1.4, zorder=0))
    ax.plot([0.35, 3], [1, 1], color="#e7e8ea", linewidth=1, zorder=0)
    ax.plot([0.70, 3], [2, 2], color="#e7e8ea", linewidth=1, zorder=0)
    ax.plot([1.5, 2.03], [0, 3], color="#e7e8ea", linewidth=1, zorder=0)
    ax.set_xlim(-0.12, 3.12)
    ax.set_ylim(3.12, -0.12)
    ax.set_xticks([0, 1.5, 3], ["前", "央", "后"])
    ax.set_yticks([0, 1, 2, 3], ["高", "中高", "中低", "低"])
    ax.tick_params(length=0, colors="#666666", labelsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_aspect("equal", adjustable="box")


def draw_main_chain(ax: plt.Axes, point: dict) -> None:
    slots = point["slots"]
    for index, (start, end) in enumerate(zip(slots, slots[1:])):
        if abs(start["x"] - end["x"]) < 1e-9 and abs(start["y"] - end["y"]) < 1e-9:
            continue
        arrow = FancyArrowPatch(
            (start["x"], start["y"]),
            (end["x"], end["y"]),
            arrowstyle="-|>",
            mutation_scale=17,
            linewidth=2.8,
            linestyle=(0, (4, 3)) if index == 0 else "solid",
            color="#2d2d2d",
            shrinkA=9,
            shrinkB=10,
            zorder=2,
        )
        ax.add_patch(arrow)

    stops = grouped_stops(slots)
    for stop in stops:
        for layer, slot in enumerate(stop["slots"]):
            radius = 105 - layer * 34
            ax.scatter(
                stop["x"],
                stop["y"],
                s=radius,
                marker="D" if slot["is_diphthong"] else "o",
                color=SLOT_COLORS[slot["slot"]],
                edgecolor="white",
                linewidth=1.1,
                zorder=4 + layer,
            )

        x, y = stop["x"], stop["y"]
        if x > 2.15:
            dx, align = -0.10, "right"
        else:
            dx, align = 0.10, "left"
        dy = 0.13 if y < 0.35 else -0.10
        text_value = stop_label(stop)
        effects = [path_effects.withStroke(linewidth=2.4, foreground="white")]
        if "ᴀ" in text_value:
            before, after = text_value.split("ᴀ", 1)
            chinese_font = fm.FontProperties(family=plt.rcParams["font.sans-serif"][0], size=11)
            ipa_font = fm.FontProperties(family="DejaVu Sans", size=11)
            parts = [
                TextArea(before, textprops={"fontproperties": chinese_font, "color": "#202124", "path_effects": effects}),
                TextArea("ᴀ", textprops={"fontproperties": ipa_font, "color": "#202124", "path_effects": effects}),
            ]
            if after:
                parts.append(TextArea(after, textprops={"fontproperties": chinese_font, "color": "#202124", "path_effects": effects}))
            packed = HPacker(children=parts, align="baseline", pad=0, sep=0)
            annotation = AnnotationBbox(
                packed,
                (x + dx, y + dy),
                xycoords="data",
                box_alignment=(1 if align == "right" else 0, 1 if dy > 0 else 0),
                frameon=False,
                pad=0,
                zorder=8,
            )
            ax.add_artist(annotation)
        else:
            label = ax.text(
                x + dx,
                y + dy,
                text_value,
                ha=align,
                va="top" if dy > 0 else "bottom",
                fontsize=11,
                color="#202124",
                zorder=8,
            )
            label.set_path_effects(effects)


def export_png(cluster: dict) -> Path:
    output = FIGS_DIR / PNG_PATTERN.format(cluster=cluster["cluster"])
    fig, ax = plt.subplots(figsize=(7.2, 5.7), facecolor="white")
    draw_frame(ax)
    draw_main_chain(ax, cluster["point"])
    ax.set_title(
        f"第{cluster['cluster']}类｜{display_type_label(cluster['type_label'])}（{cluster['size']}点）\n"
        f"代表方言点：{cluster['medoid_name']}",
        fontsize=14,
        pad=15,
    )
    fig.savefig(output, dpi=240, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    return output


def svg_xy(x: float, y: float) -> tuple[float, float]:
    return 72 + (x / 3) * 440, 32 + (y / 3) * 300


def svg_panel(cluster: dict) -> str:
    point = cluster["point"]
    slots = point["slots"]
    marker_id = f"arrow-c{cluster['cluster']}"
    pieces = [
        f'<section class="cluster-panel" aria-labelledby="cluster-{cluster["cluster"]}-title">',
        f'<h2 id="cluster-{cluster["cluster"]}-title">第{cluster["cluster"]}类｜{html.escape(display_type_label(cluster["type_label"]))}</h2>',
        f'<p class="meta">{cluster["size"]}个方言点｜主模式 {html.escape(display_chain(point))}｜代表方言点 {html.escape(cluster["medoid_name"])}</p>',
        f'<svg viewBox="0 0 550 380" role="img" aria-label="第{cluster["cluster"]}类主链：{html.escape(display_chain(point))}">',
        f'<defs><marker id="{marker_id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="context-stroke"/></marker></defs>',
        '<path class="vowel-frame" d="M72,32 L512,32 L512,332 L226,332 Z"/>',
        '<path class="grid" d="M123,132 L512,132 M175,232 L512,232 M292,32 L369,332"/>',
        '<g class="ticks"><text x="72" y="360">前</text><text x="292" y="360">央</text><text x="512" y="360">后</text><text x="58" y="36" text-anchor="end">高</text><text x="58" y="136" text-anchor="end">中高</text><text x="58" y="236" text-anchor="end">中低</text><text x="58" y="336" text-anchor="end">低</text></g>',
    ]

    for index, (start, end) in enumerate(zip(slots, slots[1:])):
        if abs(start["x"] - end["x"]) < 1e-9 and abs(start["y"] - end["y"]) < 1e-9:
            continue
        x1, y1 = svg_xy(start["x"], start["y"])
        x2, y2 = svg_xy(end["x"], end["y"])
        dashed = ' stroke-dasharray="9 7"' if index == 0 else ""
        pieces.append(
            f'<line class="chain-edge" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"{dashed} marker-end="url(#{marker_id})"/>'
        )

    for stop in grouped_stops(slots):
        x, y = svg_xy(stop["x"], stop["y"])
        for layer, slot in enumerate(stop["slots"]):
            color = SLOT_COLORS[slot["slot"]]
            radius = 8.5 - layer * 2.4
            label = html.escape(f"{SLOT_DISPLAY[slot['slot']]} {slot['value']}")
            if slot["is_diphthong"]:
                pieces.append(
                    f'<path class="slot-node" d="M{x:.1f},{y-radius:.1f} L{x+radius:.1f},{y:.1f} L{x:.1f},{y+radius:.1f} L{x-radius:.1f},{y:.1f} Z" fill="{color}"><title>{label}（复元音）</title></path>'
                )
            else:
                pieces.append(
                    f'<circle class="slot-node" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}"><title>{label}</title></circle>'
                )
        anchor = "end" if stop["x"] > 2.15 else "start"
        label_x = x - 11 if anchor == "end" else x + 11
        label_y = y + 19 if stop["y"] < 0.35 else y - 11
        pieces.append(
            f'<text class="node-label" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{html.escape(stop_label(stop))}</text>'
        )
    pieces.extend(["</svg>", "</section>"])
    return "\n".join(pieces)


def export_html(clusters: list[dict]) -> None:
    panels = "\n".join(svg_panel(cluster) for cluster in clusters)
    legend = "".join(
        f'<span><i style="--slot-color:{color}"></i>{SLOT_DISPLAY[slot]}</span>' for slot, color in SLOT_COLORS.items()
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>佳皆—麻韵—歌韵—模韵主链条聚类｜仅主链版</title>
<style>
  :root {{ color-scheme: light dark; --bg: light-dark(#fff,#181818); --fg: light-dark(#202124,#f4f4f4); --muted: light-dark(#62666b,#b7bbc0); --grid: light-dark(#dfe1e5,#494d52); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px; background: var(--bg); color: var(--fg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Arial Unicode MS", sans-serif; }}
  main {{ max-width: 1500px; margin: 0 auto; }}
  h1 {{ margin: 0 0 10px; font-size: clamp(22px,3vw,34px); font-weight: 500; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px 20px; margin-bottom: 20px; color: var(--muted); font-size: 14px; }}
  .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .legend i {{ width: 10px; height: 10px; border-radius: 50%; background: var(--slot-color); }}
  .line-key {{ width: 34px; height: 0; border-top: 3px solid var(--fg); }}
  .line-key.dashed {{ border-top-style: dashed; }}
  .cluster-grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(min(440px,100%),1fr)); gap: 22px; }}
  .cluster-panel {{ min-width: 0; }}
  h2 {{ margin: 0 0 5px; font-size: 18px; font-weight: 500; }}
  .meta {{ min-height: 42px; margin: 0 0 5px; color: var(--muted); font-size: 13px; }}
  svg {{ display: block; width: 100%; height: auto; }}
  .vowel-frame {{ fill: none; stroke: var(--grid); stroke-width: 1.5; }}
  .grid {{ fill: none; stroke: var(--grid); stroke-width: 1; opacity: .7; }}
  .ticks {{ fill: var(--muted); font-size: 13px; }}
  .ticks text:not([text-anchor]) {{ text-anchor: middle; }}
  .chain-edge {{ stroke: var(--fg); stroke-width: 3.5; vector-effect: non-scaling-stroke; }}
  .slot-node {{ stroke: var(--bg); stroke-width: 1.5; vector-effect: non-scaling-stroke; }}
  .node-label {{ fill: var(--fg); font-size: 14px; paint-order: stroke; stroke: var(--bg); stroke-width: 4px; stroke-linejoin: round; }}
  @media (max-width: 920px) {{ .cluster-grid {{ grid-template-columns: 1fr; }} .meta {{ min-height: 0; }} }}
  @media (max-width: 500px) {{ body {{ padding: 14px; }} .node-label {{ font-size: 20px; }} .ticks {{ font-size: 18px; }} }}
</style>
</head>
<body>
<main>
  <h1>佳皆—麻韵—歌韵—模韵主链条聚类｜仅主链版</h1>
  <div class="legend" aria-label="链位颜色">{legend}</div>
  <div class="cluster-grid">{panels}</div>
</main>
</body>
</html>
"""
    HTML_OUTPUT.write_text(document, encoding="utf-8")


def main() -> None:
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    set_font()
    clusters = load_clusters()
    outputs = [export_png(cluster) for cluster in clusters]
    export_html(clusters)
    print(HTML_OUTPUT.relative_to(PROJECT_ROOT))
    for output in outputs:
        print(output.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
