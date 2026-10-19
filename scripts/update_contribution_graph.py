"""Render public GitHub contributions as a local SVG; requires only Python 3."""

from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen


class ContributionsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.counts = {}
        self.tooltip_id = None
        self.tooltip_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and attrs.get("data-date"):
            self.dates[attrs["id"]] = date.fromisoformat(attrs["data-date"])
        if tag == "tool-tip":
            self.tooltip_id = attrs.get("for")
            self.tooltip_text = []

    def handle_data(self, data):
        if self.tooltip_id is not None:
            self.tooltip_text.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tooltip_id is not None:
            text = "".join(self.tooltip_text).strip()
            match = re.match(r"(No|[\d,]+) contributions? on ", text)
            if match:
                self.counts[self.tooltip_id] = (
                    0 if match[1] == "No" else int(match[1].replace(",", ""))
                )
            self.tooltip_id = None


def render(days):
    width, height = 1000, 260
    left, right, top, bottom = 55, 975, 60, 210
    peak = max(4, max(count for _, count in days))
    points = [
        (left + i * (right - left) / (len(days) - 1),
         bottom - count / peak * (bottom - top))
        for i, (_, count) in enumerate(days)
    ]
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    start, end = days[0][0], days[-1][0]
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Rui\'s Contribution Graph</title>',
        f'<desc id="desc">Daily GitHub contributions from {start} to {end}. Total: {sum(n for _, n in days)}.</desc>',
        '<rect width="1000" height="260" rx="8" fill="#1a1b27"/>',
        '<g font-family="sans-serif" font-size="12" fill="#a9b1d6">',
        '<text x="500" y="30" text-anchor="middle" font-size="20" fill="#70a5fd">Rui\'s Contribution Graph</text>',
    ]
    for i in range(5):
        y = bottom - i / 4 * (bottom - top)
        svg.extend([
            f'<path d="M{left},{y} H{right}" stroke="#30344b"/>',
            f'<text x="45" y="{y + 4}" text-anchor="end">{peak * i / 4:g}</text>',
        ])
    svg.append(f'<polygon points="{left},{bottom} {coordinates} {right},{bottom}" fill="#70a5fd" opacity="0.15"/>')
    svg.append(f'<polyline points="{coordinates}" fill="none" stroke="#70a5fd" stroke-width="2"/>')
    for i, ((day, count), (x, y)) in enumerate(zip(days, points)):
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#bf91f3"><title>{escape(str(day))}: {count} contributions</title></circle>')
        if i % 5 == 0:
            svg.append(f'<text x="{x:.2f}" y="232" text-anchor="middle">{day:%m-%d}</text>')
    svg.append('</g></svg>\n')
    return "\n".join(svg)


def main():
    request = Request(
        "https://github.com/users/imrui/contributions",
        headers={"User-Agent": "imrui-contribution-graph", "Accept-Language": "en-US"},
    )
    with urlopen(request, timeout=30) as response:
        parser = ContributionsParser()
        parser.feed(response.read().decode("utf-8"))
    today = datetime.now(timezone.utc).date()
    dates = {day: key for key, day in parser.dates.items() if day <= today}
    days = []
    for offset in range(30, -1, -1):
        day = today - timedelta(days=offset)
        key = dates.get(day)
        if key not in parser.counts:
            raise ValueError(f"Missing contribution data for {day}; keeping existing SVG")
        days.append((day, parser.counts[key]))
    output = Path(__file__).resolve().parents[1] / "assets" / "contribution-graph.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(days), encoding="utf-8")
    print(f"Updated {output.name}: {days[0][0]} to {days[-1][0]}")


if __name__ == "__main__":
    main()
