from backend.links.models import ProfileLink
from backend.profiles.models import User


class LinkRepository:
    @staticmethod
    async def find_by_id(link_id: str) -> ProfileLink | None:
        user = await User.find_one({"links.id": link_id})
        return (
            next((link for link in user.links if link.id == link_id), None)
            if user
            else None
        )
