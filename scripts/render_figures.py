# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11,<13", "pydantic>=2,<3"]
# ///
# Run: uv run scripts/render_figures.py
"""Render original engineering diagrams to both SVG and high-resolution PNG."""

import math
from html import escape
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, TypeAdapter

ROOT: Final = Path(__file__).resolve().parents[1]
FONT: Final = next(
    (
        p
        for p in (
            Path("/System/Library/Fonts/STHeiti Light.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        )
        if p.exists()
    ),
    None,
)


class Node(BaseModel):
    id: str
    label: str
    body: list[str]
    x: int | None = None
    y: int | None = None


class Diagram(BaseModel):
    number: int
    name: str
    title: str
    subtitle: str
    nodes: list[Node]
    edges: list[tuple[str, str]]
    footnote: str


def render(spec: Diagram) -> None:
    """Use the same geometry for both formats; edges sit behind readable cards."""
    width, height, scale = 1440, 1040, 2
    image = Image.new("RGB", (width * scale, height * scale), "#f4f6f3")
    draw = ImageDraw.Draw(image)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f4f6f3"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3z" fill="#7e8d84"/></marker></defs>',
    ]

    def text(position: tuple[int, int], content: str, size: int, color: str) -> None:
        x, y = position
        font = (
            ImageFont.truetype(str(FONT), size * scale)
            if FONT
            else ImageFont.load_default(size=size * scale)
        )
        draw.text((x * scale, y * scale), content, font=font, fill=color)
        svg.append(
            f'<text x="{x}" y="{y + size}" font-family="Heiti SC,Noto Sans CJK SC,sans-serif" font-size="{size}" fill="{color}">{escape(content)}</text>'
        )

    text((60, 34), f"TCM AGENT / ENGINEERING COURSE / {spec.number:02}", 18, "#557265")
    text((60, 78), spec.title, 39, "#183c30")
    text((60, 137), spec.subtitle, 20, "#52645b")
    nodes = spec.nodes
    locations: dict[str, tuple[int, int]] = {}
    for i, node in enumerate(nodes):
        x, y = (
            (node.x if node.x is not None else 60 + (i % 3) * 460),
            (node.y if node.y is not None else 220 + (i // 3) * 250),
        )
        locations[node.id] = (x, y)
    for edge in spec.edges:
        start, finish = locations[edge[0]], locations[edge[1]]
        dx, dy = finish[0] - start[0], finish[1] - start[1]
        if abs(dx) >= abs(dy):
            sign = 1 if dx > 0 else -1
            a = (start[0] + (360 if sign > 0 else 0), start[1] + 68)
            b = (finish[0] + (0 if sign > 0 else 360), finish[1] + 68)
        else:
            sign = 1 if dy > 0 else -1
            a = (start[0] + 180, start[1] + (136 if sign > 0 else 0))
            b = (finish[0] + 180, finish[1] + (0 if sign > 0 else 136))
        draw.line(
            [(a[0] * scale, a[1] * scale), (b[0] * scale, b[1] * scale)],
            fill="#7e8d84",
            width=3 * scale,
        )
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        points = [(b[0] * scale, b[1] * scale)]
        points.extend(
            (
                (b[0] - 12 * math.cos(angle + offset)) * scale,
                (b[1] - 12 * math.sin(angle + offset)) * scale,
            )
            for offset in (-0.45, 0.45)
        )
        draw.polygon(points, fill="#7e8d84")
        svg.append(
            f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="#7e8d84" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
        )
    for node in nodes:
        x, y = locations[node.id]
        draw.rounded_rectangle(
            (x * scale, y * scale, (x + 360) * scale, (y + 136) * scale),
            radius=12 * scale,
            fill="#ffffff",
            outline="#dce3dd",
            width=scale,
        )
        svg.append(
            f'<rect x="{x}" y="{y}" width="360" height="136" rx="12" fill="white" stroke="#dce3dd"/>'
        )
        text((x + 20, y + 13), f"{ord(node.id) - ord('A') + 1:02} / {node.label}", 25, "#183c30")
        for line, content in enumerate(node.body):
            text((x + 20, y + 56 + 26 * line), content, 19, "#52645b")
    text((60, 977), spec.footnote, 18, "#52645b")
    svg.append("</svg>")
    target = ROOT / "course/assets" / spec.name
    target.with_suffix(".svg").write_text("\n".join(svg), encoding="utf-8")
    image.resize((width, height), Image.Resampling.LANCZOS).save(target.with_suffix(".png"))
    mermaid = ["flowchart TD"]
    mermaid.extend(f'    {n.id}["{n.label}<br/>{" · ".join(n.body)}"]' for n in nodes)
    mermaid.extend(f"    {e[0]} --> {e[1]}" for e in spec.edges)
    target.with_suffix(".mmd").write_text("\n".join(mermaid) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for figure in TypeAdapter(list[Diagram]).validate_json(
        (ROOT / "course/assets/figures.json").read_bytes()
    ):
        render(figure)
