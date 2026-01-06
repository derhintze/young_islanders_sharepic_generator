#!/usr/bin/env python3.13

"""Create Sharepic with Cairo."""

import io
from dataclasses import dataclass

import cairo
import cairosvg
from PIL import Image, ImageEnhance, ImageFilter

_DRAW_DEBUG = False

WIDTH_PTS = 1080
HEIGHT_PTS = 1350

DPI = 96
MM_TO_UNITS = DPI / 25.4
ISLANDERS_BLUE = (12 / 255, 24 / 255, 40 / 255)
WHITE = (1, 1, 1)


class TypeScale:
    """Create a type scale."""

    def __init__(self, base_size: int, scale_ratio: float):
        """Create type scale.

        Args:
            base_size (int): Base size for body text.
            scale_ratio (float): Scale ratio to use.
        """
        self.H5 = scale_ratio * base_size
        self.H4 = scale_ratio * self.H5
        self.H3 = scale_ratio * self.H4
        self.H2 = scale_ratio * self.H3
        self.H1 = scale_ratio * self.H2
        self.BODY = base_size
        self.CAPTION = base_size / scale_ratio
        self.SMALL = self.CAPTION / scale_ratio


@dataclass
class Coordinate:
    """Simple coordinate class."""

    x_pos: float
    y_pos: float


class OverflowingHBoxError(Exception):
    """Thrown when the box of rectangles is overflowing."""

    pass


class BoxOfRectangles:
    """Box of rectangles.

    Didn't know a better name. Let me know if you have one.
    """

    RECT_H = 30.0 * MM_TO_UNITS
    RECT_W = (1 - 4 / 30) * WIDTH_PTS
    H_PAD = 1 / 30 * WIDTH_PTS

    rectangles: list[Coordinate]

    def __init__(self, n_rectangles: int, top_y, bottom_y) -> None:
        """Initialize new box of rectangles."""
        self.total_height = 0

        n_rectangles_upper_half = n_rectangles / 2
        n_pads_upper_half = n_rectangles_upper_half - 0.5

        assert top_y < bottom_y

        box_height = bottom_y - top_y
        center_of_box = top_y + box_height / 2
        y_pos_start = center_of_box - (
            n_rectangles_upper_half * self.RECT_H + n_pads_upper_half * self.H_PAD
        )

        self.rectangles = []
        current_y_pos = y_pos_start
        for rect in range(n_rectangles):
            self.rectangles.append(
                Coordinate((WIDTH_PTS - self.RECT_W) / 2, current_y_pos)
            )
            current_y_pos += self.RECT_H + self.H_PAD

        if (lowest_rect_y := current_y_pos - self.H_PAD) > bottom_y:
            msg = (
                f"The lowest rectangle ends at a y position of {lowest_rect_y}, "
                f"which is larger than the largest possible y position of {bottom_y}."
            )
            raise OverflowingHBoxError(msg)

    def __iter__(self) -> Coordinate:
        """Iterate the rectangles contained in the box."""
        yield from self.rectangles


class SharepicGenerator:
    """Sharepic Generator using Cairo SVG."""

    LOGO_WIDTH = 200  # px

    def __init__(self, n_teams: int) -> None:
        """Initialize the Sharepic Generator.

        Args:
            n_teams (int): Number of teams to use for sharepic.
        """
        self.type_scale = TypeScale(32, 1.2)

        self.surface = cairo.ImageSurface(cairo.Format.RGB24, WIDTH_PTS, HEIGHT_PTS)
        self.ctx = cairo.Context(self.surface)

        self._prepare_background()

        self.ctx.set_source_surface(self.bg_surface, 0, 0)
        self.ctx.paint()

        self._draw_logo()
        self.ctx.select_font_face(
            "Industry", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )
        top_y = self._draw_headlines(calendar_week=45)
        bottom_y = 315 * MM_TO_UNITS

        if _DRAW_DEBUG:
            self._draw_extents_of_boxes(top_y, bottom_y)

        self.rectangles = BoxOfRectangles(n_teams, top_y, bottom_y)

        self._draw_footer()

    def _prepare_background(self) -> None:
        background_image: Image.Image = Image.open("bckgrnd.jpeg")
        background_image_to_blur = background_image.filter(
            ImageFilter.GaussianBlur(radius=5)
        )
        enhancer = ImageEnhance.Brightness(background_image_to_blur)
        background_image_to_blur = enhancer.enhance(2)

        def pil_to_cairo(pil_img):
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            return cairo.ImageSurface.create_from_png(buf)

        self.bg_surface = pil_to_cairo(background_image)
        self.blurred_surface = pil_to_cairo(background_image_to_blur)

    def _draw_logo(self) -> None:
        logo_png_data = cairosvg.svg2png(
            url="evl-logo_ohne-kontur.svg", output_width=self.LOGO_WIDTH
        )
        logo_surface = cairo.ImageSurface.create_from_png(io.BytesIO(logo_png_data))

        logo_x = (WIDTH_PTS - self.LOGO_WIDTH) / 2
        logo_y = 70  # Distance from the top

        self.ctx.set_source_surface(logo_surface, logo_x, logo_y)
        self.ctx.paint()

    def _draw_headlines(self, calendar_week: int) -> float:
        text_content = "YOUNG ISLANDERS"
        self.ctx.set_font_size(self.type_scale.H1)

        extents = self.ctx.text_extents(text_content)
        text_x = (WIDTH_PTS - extents.width) / 2
        text_y = HEIGHT_PTS / 4

        self.ctx.set_source_rgb(*WHITE)
        self.ctx.move_to(text_x, text_y)
        self.ctx.show_text(text_content)

        text_content = f"SPIELVORSCHAU KW {calendar_week}"
        self.ctx.set_font_size(self.type_scale.H4)
        extents = self.ctx.text_extents(text_content)
        text_x = (WIDTH_PTS - extents.width) / 2
        text_y += 2 * extents.height
        self.ctx.move_to(text_x, text_y)
        self.ctx.show_text(text_content)

        return text_y + 0.5 * extents.height

    def _draw_extents_of_boxes(self, top_y, bottom_y) -> None:
        self.ctx.move_to(0, top_y)
        self.ctx.line_to(WIDTH_PTS, top_y)
        self.ctx.stroke()

        self.ctx.move_to(0, bottom_y)
        self.ctx.line_to(WIDTH_PTS, bottom_y)
        self.ctx.stroke()

    def _draw_footer(self) -> None:
        text_content = "www.young-islanders.com"
        self.ctx.set_font_size(self.type_scale.CAPTION)

        extents = self.ctx.text_extents(text_content)
        text_x = (WIDTH_PTS - extents.width) / 2
        text_y = 0.93 * HEIGHT_PTS

        self.ctx.set_source_rgb(*WHITE)
        self.ctx.move_to(text_x, text_y)
        self.ctx.show_text(text_content)

    def draw_frosted_rect(self, rect: Coordinate):
        """Custom function to create a frosted glass effect."""
        ctx = self.ctx
        x = rect.x_pos
        y = rect.y_pos
        w = BoxOfRectangles.RECT_W
        h = BoxOfRectangles.RECT_H

        ctx.save()
        ctx.rectangle(x, y, w, h)

        # Clip to the rectangle
        ctx.save()
        ctx.clip()
        ctx.set_source_surface(self.blurred_surface, 0, 0)
        ctx.paint()
        ctx.restore()

        # Frost overlay
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.rectangle(x, y, w, h)
        ctx.fill()

        # Glass edge
        ctx.set_source_rgba(1, 1, 1, 0.4)
        ctx.set_line_width(2)
        ctx.rectangle(x, y, w, h)
        ctx.stroke()
        ctx.restore()

    def create_svg(self) -> None:
        """Create SVG with Cairo."""
        self.ctx.set_source_rgb(*ISLANDERS_BLUE)
        for rect in self.rectangles:
            self.draw_frosted_rect(rect)

            text_content = "U17"
            self.ctx.set_font_size(self.type_scale.H3)
            extents = self.ctx.text_extents(text_content)
            text_x = 0.09 * WIDTH_PTS
            text_y = rect.y_pos + BoxOfRectangles.RECT_H / 2 + extents.height / 2
            self.ctx.move_to(text_x, text_y)
            self.ctx.show_text(text_content)

            text_content = "20.12.2025"
            self.ctx.set_font_size(self.type_scale.BODY)
            text_x += extents.width + 20
            text_y -= (
                extents.height / 2 - self.ctx.text_extents(text_content).height / 2
            )
            self.ctx.move_to(text_x, text_y)
            self.ctx.show_text(text_content)


def to_pil(surface: cairo.ImageSurface) -> Image:
    """Convert Cairo image surface to PIL Image.

    Args:
        surface (cairo.ImageSurface): Surface to convert.

    Raises:
        NotImplementedError: Raised for unknown Cairo formats.

    Returns:
        Image: PIL Image.
    """
    format = surface.get_format()
    size = (surface.get_width(), surface.get_height())
    stride = surface.get_stride()

    with surface.get_data() as memory:
        if format == cairo.Format.RGB24:
            return Image.frombuffer(
                "RGB", size, memory.tobytes(), "raw", "BGRX", stride
            )
        elif format == cairo.Format.ARGB32:
            return Image.frombuffer(
                "RGBA", size, memory.tobytes(), "raw", "BGRa", stride
            )
        else:
            raise NotImplementedError(repr(format))


if __name__ == "__main__":
    generator = SharepicGenerator(3)
    generator.create_svg()
    to_pil(generator.surface).save("final_output.jpg")
