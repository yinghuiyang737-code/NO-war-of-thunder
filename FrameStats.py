"""Small native-size frame-rate readout, independent of third-party overlays."""
import pygame
_font=None
_label=None
_value=None
def draw(surface,clock):
    global _font,_label,_value
    if _font is None:_font=pygame.font.Font(None,20)
    value=round(clock.get_fps())
    if value!=_value:
        _value=value;_label=_font.render(f'{value} FPS',True,(176,224,182))
    rect=_label.get_rect(topright=(surface.get_width()-12,5))
    pygame.draw.rect(surface,(15,24,21),rect.inflate(10,4),border_radius=3)
    surface.blit(_label,rect)
