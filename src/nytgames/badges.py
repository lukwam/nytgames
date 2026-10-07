"""NYT Games badge names, descriptions and artwork.

NYT doesn't serve badge metadata from an API: the games web app has it built
in. badges.json is a copy of that table, so it can fall behind when NYT adds
badges; `badge_info()` returns None for badges it doesn't know.
"""
import json
from functools import cache
from importlib import resources
from typing import List

from nytgames.models import NYTModel


class BadgeInfo(NYTModel):
    """A badge's name, description and artwork.

    Text and image paths can contain `{LEVEL}`, which the methods fill in
    with a level (a count, or a year for holiday badges).
    """
    uniqueId: str
    badge_type: str | None = None
    games: List[str] = []
    levels: List[int] = []
    displayName: str
    displayNameSingular: str | None = None
    descriptionBody: str = ""
    descriptionBodySingular: str | None = None
    imageUrl: str | None = None
    imageUrlUnearned: str | None = None
    imageUrlUnearnedDarkMode: str | None = None
    requiresSubscription: bool = False
    linkText: str | None = None
    linkURL: str | None = None

    @property
    def id(self) -> str:
        return self.uniqueId

    def _text(self, text: str, singular: str | None, level: int | None) -> str:
        level = self._level(level)
        if level is None:
            return text
        if level == 1 and singular:
            text = singular
        return text.replace("{LEVEL}", str(level))

    def _level(self, level: int | None) -> int | None:
        return level if level is not None else (self.levels[0] if self.levels else None)

    def name(self, level: int | None = None) -> str:
        """The badge's name at a level (default: the first level)."""
        return self._text(self.displayName, self.displayNameSingular, level)

    def description(self, level: int | None = None, earned: bool = False, times: int | None = None) -> str:
        """NYT's description, such as "You earned this badge by completing 100 ...".

        `times` is how many times a progress badge was earned.
        """
        prefixes = metadata()["descriptionPrefixes"]
        if earned and times and times > 1 and self.badge_type == "progress":
            prefix = prefixes["earnedMultiple"].replace("{AMOUNT}", str(times))
        elif earned:
            prefix = prefixes["earned"]
        else:
            prefix = prefixes["unearnedForSubscribers" if self.requiresSubscription else "unearned"]
        return prefix + self._text(self.descriptionBody, self.descriptionBodySingular, level)

    def image_url(self, level: int | None = None, earned: bool = True, dark: bool = False) -> str | None:
        """The URL of the badge's SVG artwork at a level."""
        path = self.imageUrl if earned else self.imageUrlUnearnedDarkMode if dark else self.imageUrlUnearned
        if not path:
            return None
        return metadata()["assetBase"] + self._text(path, None, level)


@cache
def metadata() -> dict:
    return json.loads(resources.files("nytgames").joinpath("badges.json").read_text(encoding="utf-8"))


@cache
def _badges() -> dict[str, BadgeInfo]:
    return {badge["uniqueId"]: BadgeInfo(**badge) for badge in metadata()["badges"]}


def all_badges(game: str | None = None) -> list[BadgeInfo]:
    """Every known badge, optionally only one game's (wordleV2, connections,
    strands or spelling_bee)."""
    return [badge for badge in _badges().values() if game is None or game in badge.games]


def badge_info(badge_id: str) -> BadgeInfo | None:
    """Return a badge's name, description and artwork, or None if unknown."""
    return _badges().get(badge_id)
