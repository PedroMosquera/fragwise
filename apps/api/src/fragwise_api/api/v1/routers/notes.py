"""Notes tree + detail. List returns hierarchical tree (no pagination)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

from fragwise_api.db.models import Fragrance, FragranceNote, Note

from ..deps import DbSession
from ..errors import not_found
from ..filters import LimitOffsetDep
from ..pagination import paginate
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceListItem
from ..schemas.note import NoteDetail, NoteTreeEnvelope, NoteTreeNode
from ..schemas.summaries import NoteSummary

router = APIRouter(prefix="/notes", tags=["Notes"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


def _to_tree_node(note: Note) -> NoteTreeNode:
    return NoteTreeNode(
        slug=note.slug,
        name=note.name,
        children=[_to_tree_node(c) for c in note.children],
    )


@router.get("", response_model=NoteTreeEnvelope)
async def list_notes(session: DbSession) -> NoteTreeEnvelope:
    stmt: Select[Any] = (
        select(Note)
        .where(Note.parent_id.is_(None))  # roots only
        .options(selectinload(Note.children, recursion_depth=10))
        .order_by(Note.name.asc(), Note.id.asc())
    )
    roots = list((await session.execute(stmt)).scalars().unique().all())
    return NoteTreeEnvelope(data=[_to_tree_node(n) for n in roots])


@router.get("/{slug}", response_model=NoteDetail)
async def get_note(
    session: DbSession,
    slug: SLUG,
    page: LimitOffsetDep,
) -> NoteDetail:
    stmt = select(Note).where(Note.slug == slug).options(joinedload(Note.parent))
    note = (await session.execute(stmt)).scalars().unique().one_or_none()
    if note is None:
        raise not_found("Note", slug)

    frag_stmt: Select[Any] = (
        select(Fragrance)
        .where(
            Fragrance.id.in_(
                select(FragranceNote.fragrance_id).where(FragranceNote.note_id == note.id)
            )
        )
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())
    )
    rows, total = await paginate(session, frag_stmt, limit=page.limit, offset=page.offset)
    return NoteDetail(
        slug=note.slug,
        name=note.name,
        parent=NoteSummary.model_validate(note.parent) if note.parent is not None else None,
        fragrances=ListEnvelope[FragranceListItem](
            data=[FragranceListItem.model_validate(r) for r in rows],
            pagination=Pagination(
                limit=page.limit,
                offset=page.offset,
                total=total,
                has_next=page.offset + page.limit < total,
            ),
        ),
    )
