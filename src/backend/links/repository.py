from backend.links.models import ProfileLink
from backend.profiles.models import User


class LinkRepository:
    """Lookup of embedded profile links by their stable identities."""

    @staticmethod
    async def find_by_id(link_id: str) -> ProfileLink | None:
        """Find a saved profile link by its stable identity.

        :param link_id: Stable identity of the saved profile link.
        :return: The matching embedded link, or None when absent.
        """
        user = await User.find_one({"links.id": link_id})

        return next((link for link in user.links if link.id == link_id), None) if user else None
