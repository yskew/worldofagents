from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.human import Human


async def get_or_create_human(
    db: AsyncSession, clerk_id: str, display_name: str, email: str | None = None
) -> Human:
    result = await db.execute(select(Human).where(Human.clerk_id == clerk_id))
    human = result.scalar_one_or_none()

    if human is None:
        human = Human(clerk_id=clerk_id, display_name=display_name, email=email)
        db.add(human)
        await db.commit()
        await db.refresh(human)
    else:
        updated = False
        if human.display_name != display_name:
            human.display_name = display_name
            updated = True
        if human.email != email:
            human.email = email
            updated = True
        if updated:
            await db.commit()
            await db.refresh(human)

    return human
