from backend.links.platforms import validate_link_url
from backend.links.repository import LinkRepository


class LinkService:
    """Resolution of saved links to their current redirect destinations."""

    async def destination(self, link_id: str) -> str | None:
        """Resolve a saved destination; future attribution belongs in this service.

        :param link_id: Stable identity of the saved profile link.
        :return: The saved HTTP or HTTPS destination URL.
        """
        link = await LinkRepository.find_by_id(link_id)

        if link is None:
            return None

        return validate_link_url(link.url)
