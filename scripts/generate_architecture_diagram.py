"""Generate report-ready PNG and SVG architecture diagrams."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "reports" / "assets"
PNG_OUTPUT = OUTPUT_DIR / "nyc_taxi_pipeline_architecture.png"
SVG_OUTPUT = OUTPUT_DIR / "nyc_taxi_pipeline_architecture.svg"

WIDTH, HEIGHT = 2400, 1500
NAVY = "#17365D"
BLUE = "#2F75B5"
LIGHT_BLUE = "#EAF3FA"
GREEN = "#2E7D5B"
LIGHT_GREEN = "#EAF5EF"
AMBER = "#B66A14"
LIGHT_AMBER = "#FFF5E6"
RED = "#B54A4A"
LIGHT_RED = "#FBEDED"
INK = "#17212B"
MUTED = "#52616F"
LINE = "#AEBCC8"
WHITE = "#FFFFFF"


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/aptos-display-bold.ttf" if bold else "C:/Windows/Fonts/aptos.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def rounded_box(draw, box, fill, outline, title, lines, accent):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=20, fill=fill, outline=outline, width=3)
    draw.rounded_rectangle((x1, y1, x1 + 15, y2), radius=8, fill=accent)
    draw.text((x1 + 40, y1 + 28), title, font=font(30, True), fill=INK)
    y = y1 + 76
    for line in lines:
        draw.text((x1 + 40, y), line, font=font(22), fill=MUTED)
        y += 34


def arrow(draw, start, end, color=BLUE, width=7, label=None):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 22 * direction, y2 - 13), (x2 - 22 * direction, y2 + 13)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 13, y2 - 22 * direction), (x2 + 13, y2 - 22 * direction)]
    draw.polygon(points, fill=color)
    if label:
        bbox = draw.textbbox((0, 0), label, font=font(19, True))
        tx = (x1 + x2 - (bbox[2] - bbox[0])) / 2
        ty = (y1 + y2) / 2 - 30
        draw.rounded_rectangle((tx - 10, ty - 4, tx + bbox[2] - bbox[0] + 10, ty + 27), 6, fill=WHITE)
        draw.text((tx, ty), label, font=font(19, True), fill=color)


def build_png():
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)

    draw.text((100, 55), "NYC Taxi Batch Pipeline", font=font(50, True), fill=NAVY)
    draw.text((100, 120), "Logical architecture and end-to-end data flow", font=font(27), fill=MUTED)

    # Docker Compose deployment boundary
    draw.rounded_rectangle((340, 220, 2290, 1360), radius=28, fill="#FAFCFD", outline=LINE, width=3)
    draw.text((380, 245), "DOCKER COMPOSE ENVIRONMENT", font=font(21, True), fill=MUTED)

    # External source
    rounded_box(draw, (70, 500, 300, 710), LIGHT_BLUE, BLUE, "NYC TLC", ["Monthly Yellow", "and Green", "Parquet files"], BLUE)

    # Pipeline container
    draw.rounded_rectangle((380, 320, 1080, 1020), radius=24, fill=WHITE, outline=BLUE, width=4)
    draw.text((420, 350), "ON-DEMAND PIPELINE CONTAINER", font=font(22, True), fill=BLUE)
    rounded_box(draw, (430, 420, 730, 610), LIGHT_BLUE, BLUE, "Extract", ["Requests streaming", "Atomic .part rename", "SHA-256 checksum"], BLUE)
    rounded_box(draw, (780, 420, 1030, 610), LIGHT_AMBER, AMBER, "Transform", ["PyArrow chunks", "Pandas canonical", "schema mapping"], AMBER)
    rounded_box(draw, (605, 730, 875, 920), LIGHT_GREEN, GREEN, "Validate", ["Business rules", "Valid / invalid split", "50k-row batches"], GREEN)
    arrow(draw, (730, 515), (780, 515))
    arrow(draw, (905, 610), (810, 730))

    # Bronze is persisted on a host-mounted volume.
    rounded_box(draw, (430, 1080, 1030, 1290), LIGHT_BLUE, BLUE, "Bronze filesystem", ["Raw partitioned Parquet", "data/bronze/{type}/{year}/{month}", "Replayable source of truth"], BLUE)
    arrow(draw, (580, 610), (580, 1080), label="persist")
    arrow(draw, (860, 1080), (860, 610), label="read chunks")

    # PostgreSQL container and logical schemas
    draw.rounded_rectangle((1160, 320, 1835, 1290), radius=24, fill=WHITE, outline=GREEN, width=4)
    draw.text((1200, 350), "POSTGRESQL 16 CONTAINER", font=font(22, True), fill=GREEN)
    rounded_box(draw, (1210, 420, 1785, 610), LIGHT_GREEN, GREEN, "Silver: canonical trips", ["Typed and validated records", "Latest successful monthly batch", "Row-level source lineage"], GREEN)
    rounded_box(draw, (1210, 680, 1785, 900), LIGHT_AMBER, AMBER, "Gold: analytical data", ["yellow_trips / green_trips", "trip_key primary-key deduplication", "monthly_summary materialized view"], AMBER)
    rounded_box(draw, (1210, 970, 1785, 1210), LIGHT_RED, RED, "Pipeline operations", ["batch_runs and file_ingestions", "rejected_records + reasons", "Checksums, counters and errors"], RED)
    arrow(draw, (1497, 610), (1497, 680), label="promote")

    # Dashboard container
    rounded_box(draw, (1920, 485, 2240, 770), LIGHT_BLUE, BLUE, "Streamlit", ["Overview and KPIs", "Runs and quality", "Analytics and lineage", "Read-only SQL"], BLUE)
    arrow(draw, (1920, 570), (1785, 570), color=GREEN, label="query")
    arrow(draw, (1785, 790), (1920, 690), color=GREEN)

    # Main data paths from validation.
    arrow(draw, (875, 810), (1210, 515), color=GREEN, label="valid rows")
    arrow(draw, (875, 855), (1210, 1090), color=RED, label="invalid rows")
    arrow(draw, (300, 605), (430, 515), label="HTTPS")

    # Transaction annotation and legend.
    draw.rounded_rectangle((1185, 395, 1810, 1255), radius=25, outline="#7F8C97", width=3)
    draw.text((1208, 1230), "Atomic monthly database transaction", font=font(20, True), fill=MUTED)
    draw.text((100, 1410), "Solid arrows: data movement   |   PostgreSQL volume and Bronze host mount provide persistence", font=font(22), fill=MUTED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image.save(PNG_OUTPUT, dpi=(200, 200), optimize=True)


def build_svg():
    # Embed the high-resolution PNG in an SVG wrapper so office and design tools can
    # import the same composition at a predictable 12:7.5 aspect ratio.
    import base64

    encoded = base64.b64encode(PNG_OUTPUT.read_bytes()).decode("ascii")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1500" viewBox="0 0 2400 1500">
  <title>NYC Taxi Batch Pipeline logical architecture</title>
  <image width="2400" height="1500" href="data:image/png;base64,{encoded}"/>
</svg>'''
    SVG_OUTPUT.write_text(svg, encoding="ascii")


def main():
    build_png()
    build_svg()
    print(PNG_OUTPUT)
    print(SVG_OUTPUT)


if __name__ == "__main__":
    main()
