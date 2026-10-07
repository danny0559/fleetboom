"""Shared image decoding and sprite-size cache."""
from PIL import Image, ImageTk
from .config import ASSETS


class ArtCache:
    """Share decoded artwork and pre-sized sprites between all six active bodies."""
    def __init__(self, master):
        self.master = master
        with Image.open(ASSETS / "blackhole-v2.png") as image:
            self.blackhole = image.convert("RGBA")
        self.frames = {}

    def hole(self, step):
        if step not in self.frames:
            width = 36 + step * 20
            image = self.blackhole.resize((width, round(width*2/3)), Image.Resampling.LANCZOS)
            self.frames[step] = ImageTk.PhotoImage(image, master=self.master)
        return self.frames[step]
