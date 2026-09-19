"""Renderiza cards 9:16 autorizados por gerar_carrossel=sim."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

import executar_flow as flow
from preparar_insumos import ROOT, Invalid, Workbook, digest, norm, now, require, signature

WIDTH, HEIGHT = 1080, 1920
SIDE, TOP, BOTTOM = 96, 160, 220
WINE = (143, 50, 76, 238)
CREAM = (255, 248, 239, 255)
INK = (91, 35, 51, 255)


def font_path(*names):
    roots = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    for root in roots:
        for name in names:
            path = root / name
            if path.is_file():
                return str(path)
    raise Invalid("Fonte local compatível não encontrada.")


SERIF = font_path("georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf")
SANS_BOLD = font_path("arialbd.ttf", "DejaVuSans-Bold.ttf")
SANS = font_path("arial.ttf", "DejaVuSans.ttf")


def wrap(draw, text, font, max_width, max_lines):
    words = text.strip().split()
    lines = []
    for word in words:
        candidate = (lines[-1] + " " + word).strip() if lines else word
        if lines and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(word)
        elif lines:
            lines[-1] = candidate
        else:
            lines.append(word)
    require(len(lines) <= max_lines, f"Texto não cabe em {max_lines} linhas: {text}")
    return lines


def fitted(draw, text, path, maximum, minimum, max_width, max_lines):
    for size in range(maximum, minimum - 1, -2):
        font = ImageFont.truetype(path, size)
        try:
            return font, wrap(draw, text, font, max_width, max_lines)
        except Invalid:
            continue
    raise Invalid(f"Texto não cabe na área segura: {text}")


def centered_lines(draw, lines, font, y, fill, spacing=10, stroke=0):
    heights = [draw.textbbox((0, 0), line, font=font, stroke_width=stroke)[3] for line in lines]
    for line, height in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=stroke)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke, stroke_fill=(55, 20, 30, 180))
        y += height + spacing
    return y


def cover(source):
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - WIDTH) // 2)
    top = max(0, (resized.height - HEIGHT) // 2)
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))



def render(source, destination, carousel, papel="principal"):
    require(len(carousel["texto"]) <= 52, "texto_carrossel excede 52 caracteres.")
    require(len(carousel["subtexto"]) <= 28, "subtexto_carrossel excede 28 caracteres.")
    cta_text = carousel.get("cta", "") or ""
    require(len(cta_text) <= 54, "CTA excede 54 caracteres.")
    base = ImageEnhance.Color(cover(source)).enhance(0.92).convert("RGBA")
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = shade.load()
    for y in range(HEIGHT):
        top_alpha = max(0, int(145 * (1 - y / 720)))
        bottom_alpha = max(0, int(120 * ((y - 1180) / 740)))
        alpha = max(top_alpha, bottom_alpha)
        for x in range(WIDTH):
            pixels[x, y] = (44, 17, 26, alpha)
    base = Image.alpha_composite(base, shade)
    draw = ImageDraw.Draw(base)
    max_width = WIDTH - 2 * SIDE

    title = carousel["texto"].upper()
    title_font, title_lines = fitted(draw, title, SERIF, 91, 58, max_width, 3)

    # Abertura/capa usa o texto mais centralizado.
    if papel in {"abertura", "cta"}:
        title_y = 340
    else:
        title_y = TOP

    y = centered_lines(
        draw,
        title_lines,
        title_font,
        title_y,
        "white",
        spacing=7,
        stroke=2
    ) + 34
    sub_font, sub_lines = fitted(draw, carousel["subtexto"], SANS_BOLD, 45, 30, max_width - 92, 2)
    line_h = sub_font.getbbox("Ag")[3] - sub_font.getbbox("Ag")[1]
    band_h = len(sub_lines) * (line_h + 8) + 38
    draw.rounded_rectangle((SIDE + 28, y, WIDTH - SIDE - 28, y + band_h), radius=22, fill=WINE)
    centered_lines(draw, sub_lines, sub_font, y + 17, CREAM, spacing=8)

    if cta_text:
        cta_font, cta_lines = fitted(draw, cta_text, SANS_BOLD, 42, 28, max_width - 96, 2)
        cta_line_h = cta_font.getbbox("Ag")[3] - cta_font.getbbox("Ag")[1]
        box_h = len(cta_lines) * (cta_line_h + 10) + 48
        cta_y = HEIGHT - BOTTOM - box_h
        draw.rounded_rectangle((SIDE, cta_y, WIDTH - SIDE, cta_y + box_h), radius=28, fill=CREAM)
        centered_lines(draw, cta_lines, cta_font, cta_y + 22, INK, spacing=10)

    destination.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destination, "PNG", optimize=True)


def carousel_frame(clip, row, state):
    require(norm(row["gerar_carrossel"]) == "sim", "Carrossel nao autorizado na planilha.")
    frame = flow.media(state["imagem"]) if state.get("imagem") else flow.existing(clip, "frame_existente_ref_id")
    return frame


def generate(clip, sheet):
    carousel = clip["plan"].get("carrossel")
    require(
        isinstance(carousel, dict) and carousel.get("ativo") is True,
        "Carrossel não solicitado neste plano."
    )

    state = flow.state_for(clip)
    wb = Workbook(sheet)
    row = flow.row_for(wb, clip)
    frame = carousel_frame(clip, row, state)

    print(
        f"[carrossel] ordem={row['ordem']} "
        f"clipe={clip['plan']['id_clipe']} "
        f"papel={row['papel_na_producao']} "
        f"frame={frame} "
        f"texto={carousel['texto']}"
    )

    token = signature({
        "imagem": digest(frame),
        "carrossel": carousel
    })[:12]

    destination = (
        ROOT
        / "entregas_flow"
        / "carrossel"
        / clip["plan"]["producao_id"]
        / f"{clip['plan']['id_clipe']}_carrossel_{token}.png"
    )

    papel = norm(row.get("papel_na_producao", ""))

    if not destination.is_file():
        render(frame, destination, carousel, papel=papel)

    state["carrossel"] = {
        "arquivo": str(destination),
        "sha256": digest(destination),
        "origem_sha256": digest(frame),
        "em": now()
    }

    flow.atomic(clip["folder"] / "execucao.json", state)

    wb = Workbook(sheet)
    row = flow.row_for(wb, clip)

    for field, value in {
        "texto_carrossel": carousel["texto"],
        "subtexto_carrossel": carousel["subtexto"],
        "carrossel_status": "gerado",
        "carrossel_arquivo": str(destination),
        "atualizado_em": now(),
        "erro": ""
    }.items():
        wb.set(row["_linha"], field, value)

    wb.save()
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producao", required=True, type=Path)
    parser.add_argument("--clipe")
    parser.add_argument("--planilha", type=Path, default=ROOT / "entradas/controle_pipeline_flow.xlsx")
    args = parser.parse_args()
    try:
        clips = flow.load_clips(args.producao)
        if args.clipe:
            clips = [clip for clip in clips if clip["plan"]["id_clipe"] == args.clipe]
        require(bool(clips), "Nenhum clipe selecionado.")
        for clip in clips:
            if isinstance(clip["plan"].get("carrossel"), dict) and clip["plan"]["carrossel"].get("ativo"):
                print(generate(clip, args.planilha))
        return 0
    except (Invalid, OSError, ValueError, KeyError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
