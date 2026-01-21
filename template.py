#!/usr/bin/env python3.13

"""Create Sharepic with Cairo."""

import io
from dataclasses import dataclass

import cairo
import cairosvg
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter

import consts

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

    LOGO_WIDTH = 200
    VS_WIDTH = 80

    def __init__(
        self, game_data: pd.DataFrame, title: str, week: int, scores: bool = False
    ) -> None:
        """Initialize the Sharepic Generator.

        Args:
            game_data (pd.DataFrame): Game data.
            title (str): Title, which is actually some kind of subtitle, since the real
                title is "YOUNG ISLANDERS".
            week (int): Week to create sharepic for.
            scores (bool, optional): Whether to print scores instead of times.
        """
        self.game_data = game_data.loc[
            game_data[consts.DATE_COL].dt.isocalendar().week == week
        ].set_index(consts.TEAMS_COL)
        n_teams = len(set(self.game_data.index) - ({"U11", "U9"} if scores else set()))
        self.scores = scores
        self.type_scale = TypeScale(32, 1.2)

        self.surface = cairo.ImageSurface(cairo.Format.RGB24, WIDTH_PTS, HEIGHT_PTS)
        self.ctx = cairo.Context(self.surface)

        self.vs_symbol = cairosvg.svg2png(url="vs.svg", output_width=self.VS_WIDTH)

        self._prepare_background()

        self.ctx.set_source_surface(self.bg_surface, 0, 0)
        self.ctx.paint()

        self._draw_logo()
        self.ctx.select_font_face(
            "Industry", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )
        top_y = self._draw_headlines(title, calendar_week=week)
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

    def _draw_headlines(self, title, calendar_week: int) -> float:
        text_content = "YOUNG ISLANDERS"
        self.ctx.set_font_size(self.type_scale.H1)

        extents = self.ctx.text_extents(text_content)
        text_x = (WIDTH_PTS - extents.width) / 2
        text_y = HEIGHT_PTS / 4

        self.ctx.set_source_rgb(*WHITE)
        self.ctx.move_to(text_x, text_y)
        self.ctx.show_text(text_content)

        text_content = f"{title} KW {calendar_week}"
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

    def draw_frosted_rect(self, rect: Coordinate) -> None:
        """Custom function to create a frosted glass effect.

        Args:
            rect (Coordinate): Coordinate for rectangle.
        """
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

    def draw_rect(self, rect: Coordinate) -> None:
        """Draw a simple, white rectangle.

        Args:
            rect (Coordinate): Coordinate for rectangle.
        """
        self.ctx.set_source_rgb(*WHITE)
        self.ctx.rectangle(
            rect.x_pos, rect.y_pos, BoxOfRectangles.RECT_W, BoxOfRectangles.RECT_H
        )
        self.ctx.fill()

    def __call__(self) -> None:
        """Generate the sharepic."""
        for rect, team in zip(self.rectangles, self.game_data.index.unique()):
            if self.scores and team in {"U11", "U9"}:
                # no scores for them, sry
                continue
            data = self.game_data.loc[[team]]
            dates = data[consts.DATE_COL].dt.strftime(consts.DATE_FMT).to_list()
            opponents = data[consts.VS_COL].to_list()
            vals = data[consts.GOALS_COL if self.scores else consts.TIME_COL].to_list()
            self.draw_rect(rect)

            self._draw_vs(0.38 * WIDTH_PTS, rect.y_pos)

            self.ctx.set_source_rgb(*ISLANDERS_BLUE)

            self._write_text_at(
                text_x=0.09 * WIDTH_PTS,
                text_y=rect.y_pos,
                text_content=team,
                font_size=self.type_scale.H3,
            )

            self._write_text_at(
                text_x=0.2 * WIDTH_PTS,
                text_y=rect.y_pos,
                text_content=dates,
                font_size=self.type_scale.BODY,
            )

            self._write_text_at(
                text_x=0.475 * WIDTH_PTS,
                text_y=rect.y_pos,
                text_content=opponents,
                font_size=self.type_scale.BODY,
            )

            lefts = []
            rights = []
            left_x_pos = []
            x_pos = 0.86 * WIDTH_PTS
            for val in vals:
                self.ctx.set_font_size(self.type_scale.BODY)

                colon_extents = self.ctx.text_extents(":")
                right_x_pos = x_pos + colon_extents.x_advance

                left, right = val.split(":")
                extents = self.ctx.text_extents(left)
                lefts.append(left)
                rights.append(right)
                left_x_pos.append(x_pos - extents.x_advance)

            self._write_text_at(
                text_x=left_x_pos,
                text_y=rect.y_pos,
                text_content=lefts,
                font_size=self.type_scale.BODY,
            )
            self._write_text_at(
                text_x=x_pos,
                text_y=rect.y_pos,
                text_content=len(vals) * [":"],
                font_size=self.type_scale.BODY,
            )
            self._write_text_at(
                text_x=right_x_pos,
                text_y=rect.y_pos,
                text_content=rights,
                font_size=self.type_scale.BODY,
            )

        return self.to_pil()

    def _write_text_at(
        self,
        text_x: float | list[float],
        text_y: float,
        text_content: str | list[str],
        font_size: float,
    ) -> None:
        if isinstance(text_content, str):
            text_content = [text_content]

        if isinstance(text_x, float):
            text_x = len(text_content) * [text_x]

        self.ctx.set_font_size(font_size)

        ascent, descent, *_ = self.ctx.font_extents()
        line_spacing = 13

        single_line_height = ascent + descent
        total_text_height = (len(text_content) * single_line_height) + (
            (len(text_content) - 1) * line_spacing
        )

        start_y = text_y + (BoxOfRectangles.RECT_H - total_text_height) / 2

        for i, (text, line_x) in enumerate(zip(text_content, text_x)):
            line_y = start_y + (i * (single_line_height + line_spacing)) + ascent

            self.ctx.move_to(line_x, line_y)
            self.ctx.show_text(text)

    def _draw_vs(self, x_pos: float, y_pos: float) -> None:
        vs_surf = cairo.ImageSurface.create_from_png(io.BytesIO(self.vs_symbol))
        self.ctx.set_source_surface(
            vs_surf,
            x_pos,
            y_pos + BoxOfRectangles.RECT_H / 2 - vs_surf.get_height() / 2,
        )
        self.ctx.paint()

    def to_pil(self) -> Image:
        """Convert Cairo image surface to PIL Image.

        Args:
            surface (cairo.ImageSurface): Surface to convert.

        Raises:
            NotImplementedError: Raised for unknown Cairo formats.

        Returns:
            Image: PIL Image.
        """
        size = (self.surface.get_width(), self.surface.get_height())
        stride = self.surface.get_stride()

        with self.surface.get_data() as memory:
            return Image.frombuffer(
                "RGB", size, memory.tobytes(), "raw", "BGRX", stride
            )
