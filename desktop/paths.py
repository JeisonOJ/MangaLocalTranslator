"""Resolve the selected manga/chapter structure without creating directories."""
from pathlib import Path


def output_chapter(source, base):
    source = Path(source).expanduser().resolve(strict=True)
    base = Path(base).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('Select an input chapter folder.')
    manga = source.parent
    if not manga.name or manga == manga.parent:
        raise ValueError('The chapter folder must be inside a named manga folder.')
    if base.exists() and not base.is_dir():
        raise ValueError('The output base must be a folder.')
    destination = (base / manga.name / source.name).resolve()
    if not destination.is_relative_to(base):
        raise ValueError('An existing output folder redirects outside the selected base. Choose a different output base.')
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('The resolved output overlaps the source chapter. Choose a different output base.')
    return destination
