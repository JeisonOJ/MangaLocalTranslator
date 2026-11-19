"""Whole-word fitting and measured centering adapted from evaluation Run-02."""
from PIL import Image, ImageDraw, ImageFont


def layout(image, text, box, font_path, preferred=32):
    x1, y1, x2, y2 = box
    width, height = x2 - x1 - 4, y2 - y1 - 4
    words = text.split()
    if not words or width < 1 or height < 1:
        return None
    draw = ImageDraw.Draw(image)
    # Keep whole words. Choose the fewest lines, then the most even widths.
    for size in range(preferred, 5, -1):
        font = ImageFont.truetype(str(font_path), size)
        best = {len(words): (0, 0, [])}
        for start in range(len(words) - 1, -1, -1):
            for end in range(start + 1, len(words) + 1):
                line = ' '.join(words[start:end])
                bbox = draw.textbbox((0, 0), line, font=font)
                ink_width = bbox[2] - bbox[0]
                if max(ink_width, draw.textlength(line, font=font)) > width:
                    break
                if end in best:
                    count, score, tail = best[end]
                    candidate = (count + 1, score + (width - ink_width)**2, [(line, bbox), *tail])
                    if start not in best or candidate[:2] < best[start][:2]:
                        best[start] = candidate
        if 0 not in best:
            continue
        lines = best[0][2]
        line_height = max(b[3] - b[1] for _, b in lines)
        gap = round(size * .2)
        block_height = line_height * len(lines) + gap * (len(lines) - 1)
        if block_height > height:
            continue
        ink = Image.new('L', (x2 - x1, y2 - y1))
        painter = ImageDraw.Draw(ink)
        top = (ink.height - block_height) / 2
        for line, (left, upper, right, _) in lines:
            x = (ink.width - (right - left)) / 2 - left
            painter.text((round(x), round(top - upper)), line, font=font, fill=255)
            top += line_height + gap
        if ink.getbbox():
            return ink, size
    return None
