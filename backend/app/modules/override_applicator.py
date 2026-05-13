"""
override_applicator.py
======================
Applies ManualOverride text fields to Product rows, winning over sheet/scrape values.

Used by all three sync paths: Full Sync, Update List apply, Quick Price Update.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manual_override import ManualOverride
from app.models.product import Product

TEXT_OVERRIDE_TARGET_FIELD: dict[str, str] = {
    "product_price": "formatted_price",
    "product_description": "scraped_name",
    "product_pack_of": "pack_of",
    "product_quantity": "quantity",
    "product_discount": "discount",
}


async def apply_text_overrides(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    product_ids: list[uuid.UUID],
) -> None:
    """Apply ManualOverride text fields to the given products, winning over sheet values.

    For each product in *product_ids*, if a ManualOverride row exists for a text
    target_type, that value is written to the corresponding Product field and wins
    over whatever the sync materialised from the sheet/scrape.

    This is the inverse of the mapping defined in PATCH /products/{id}:
        product_price       → formatted_price
        product_description → scraped_name
        product_pack_of     → pack_of
        product_quantity    → quantity
        product_discount    → discount
    """
    if not product_ids:
        return

    pid_strs = [str(p) for p in product_ids]
    mo_result = await session.execute(
        select(ManualOverride).where(
            ManualOverride.campaign_id == campaign_id,
            ManualOverride.target_type.in_(TEXT_OVERRIDE_TARGET_FIELD.keys()),
            ManualOverride.target_id.in_(pid_strs),
        )
    )
    overrides = mo_result.scalars().all()
    if not overrides:
        return

    pid_to_overrides: dict[str, dict[str, str]] = {}
    for mo in overrides:
        if mo.target_id:
            pid_to_overrides.setdefault(mo.target_id, {})[mo.target_type] = mo.override_url

    for pid_str, type_map in pid_to_overrides.items():
        try:
            prod_uuid = uuid.UUID(pid_str)
        except ValueError:
            continue
        prod_result = await session.execute(
            select(Product).where(
                Product.id == prod_uuid,
                Product.campaign_id == campaign_id,
            )
        )
        product = prod_result.scalar_one_or_none()
        if product is None:
            continue
        for target_type, value in type_map.items():
            field = TEXT_OVERRIDE_TARGET_FIELD.get(target_type)
            if field:
                setattr(product, field, value)
