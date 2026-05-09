import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign, CampaignStatus
from app.models.product import Product, Section
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignRead,
    CampaignUpdate,
)

router = APIRouter()


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    status: Optional[CampaignStatus] = Query(None),
    show_archived: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> CampaignListResponse:
    query = select(Campaign).where(Campaign.owner_id == user.id)
    count_query = select(func.count()).select_from(Campaign).where(
        Campaign.owner_id == user.id
    )

    if not show_archived:
        query = query.where(Campaign.archived == False)  # noqa: E712
        count_query = count_query.where(Campaign.archived == False)  # noqa: E712

    if status is not None:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)

    query = query.order_by(Campaign.updated_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    campaigns = result.scalars().all()

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return CampaignListResponse(items=list(campaigns), total=total)


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Campaign:
    campaign = Campaign(
        name=data.name,
        sheet_url=data.sheet_url,
        owner_id=user.id,
    )
    session.add(campaign)
    await session.flush()
    await session.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Campaign:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Campaign:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    await session.flush()
    await session.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> dict:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    await session.delete(campaign)
    await session.commit()
    return {}


@router.post("/{campaign_id}/duplicate", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def duplicate_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Campaign:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    original = result.scalar_one_or_none()
    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    new_campaign = Campaign(
        name=f"{original.name} (Copy)",
        sheet_url=original.sheet_url,
        status=CampaignStatus.draft,
        owner_id=user.id,
    )
    session.add(new_campaign)
    await session.flush()
    await session.refresh(new_campaign)

    # Copy sections and build old->new section id mapping
    sections_result = await session.execute(
        select(Section).where(Section.campaign_id == campaign_id)
    )
    old_sections = sections_result.scalars().all()
    section_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for old_section in old_sections:
        new_section = Section(
            campaign_id=new_campaign.id,
            title=old_section.title,
            position=old_section.position,
            locked=old_section.locked,
        )
        session.add(new_section)
        await session.flush()
        await session.refresh(new_section)
        section_id_map[old_section.id] = new_section.id

    # Copy products
    products_result = await session.execute(
        select(Product).where(Product.campaign_id == campaign_id)
    )
    old_products = products_result.scalars().all()
    for old_product in old_products:
        new_section_id = section_id_map.get(old_product.section_id) if old_product.section_id else None
        new_product = Product(
            campaign_id=new_campaign.id,
            section_id=new_section_id,
            sku=old_product.sku,
            product_link=old_product.product_link,
            priority=old_product.priority,
            raw_price=old_product.raw_price,
            formatted_price=old_product.formatted_price,
            utm_campaign=old_product.utm_campaign,
            utm_stitched=old_product.utm_stitched,
            button_name=old_product.button_name,
            scraped_name=old_product.scraped_name,
            scraped_image_url=old_product.scraped_image_url,
            processed_image_url=old_product.processed_image_url,
            scrape_failed=old_product.scrape_failed,
            position=old_product.position,
        )
        session.add(new_product)

    await session.flush()
    await session.refresh(new_campaign)
    return new_campaign


@router.patch("/{campaign_id}/archive", response_model=CampaignRead)
async def archive_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Campaign:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    campaign.archived = True
    await session.flush()
    await session.refresh(campaign)
    return campaign
