"""Audience profile store: sync from collected social data, import from anywhere.

Nothing here judges or labels people. Sync only *collects* evidence that the
pipeline already stored (profile fields, inferred demographics, NLP outputs,
recent posts) into one open-ended record per account. Grouping is done later
by the model in ``segmentation.py``.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.audience_lab.models import AudienceProfile
from app.audience_lab.schemas import ProfileIn, UpsertResult
from app.db.models import NLPAnalysis, SocialEvent, SocialUser, UserDemographic
from app.demographics.geography import country_label_for_code

SOCIAL_SOURCE = "social"
MAX_EVENTS = 20_000
SAMPLE_TEXTS = 5
TEXT_CHARS = 280


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value and value.lower() != "unknown" else None
    return value


def _pct(counter: Counter, total: int) -> dict[str, int]:
    return {key: round(100 * count / total) for key, count in counter.most_common()} if total else {}


def build_social_profiles(session: Session) -> list[ProfileIn]:
    """Collect one profile per social account from non-replay events."""
    replay = func.coalesce(SocialEvent.source_metadata["replay"].as_boolean(), False)
    rows = session.execute(
        select(SocialEvent, NLPAnalysis)
        .outerjoin(NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id)
        .where(replay.is_(False))
        .order_by(SocialEvent.created_at.desc())
        .limit(MAX_EVENTS)
    ).all()
    by_author: dict[Any, list[tuple[SocialEvent, NLPAnalysis | None]]] = defaultdict(list)
    for event, nlp in rows:
        by_author[event.author_id].append((event, nlp))
    if not by_author:
        return []
    users = {u.user_id: u for u in session.scalars(select(SocialUser).where(SocialUser.user_id.in_(list(by_author))))}
    demos = {d.user_id: d for d in session.scalars(select(UserDemographic).where(UserDemographic.user_id.in_(list(by_author))))}

    profiles: list[ProfileIn] = []
    for author_id, events in by_author.items():
        user = users.get(author_id)
        if user is None:
            continue
        demo = demos.get(author_id)
        attributes: dict[str, Any] = {
            "platform": user.platform,
            "bio": _clean(user.bio)[:300] if _clean(user.bio) else None,
            "self_reported_location": _clean(user.location_raw),
            "followers": user.followers_count,
            "following": user.following_count,
            "verified": user.is_verified,
        }
        if demo is not None:
            attributes.update({
                "age_bracket": _clean(demo.age_bracket),
                "country": _clean(country_label_for_code(demo.inferred_country)),
                "region": _clean(demo.inferred_region),
                "language": _clean(demo.primary_language),
                "profession": _clean(demo.professional_sector),
                "gender": _clean(demo.gender) if (demo.gender_confidence or 0) >= 0.6 else None,
            })
        attributes = {k: v for k, v in attributes.items() if v not in (None, "", [])}

        sentiments: Counter = Counter()
        emotions: Counter = Counter()
        kinds: Counter = Counter()
        tags: Counter = Counter()
        ironic = analysed = 0
        likes = shares = comments = 0
        for event, nlp in events:
            kinds[event.interaction_type] += 1
            tags.update(tag.lower() for tag in (event.hashtags or []))
            metrics = event.metrics or {}
            likes += int(metrics.get("likes") or 0)
            shares += int(metrics.get("shares") or 0)
            comments += int(metrics.get("comments") or 0)
            if nlp is not None:
                analysed += 1
                sentiments[nlp.sentiment_label] += 1
                ironic += int(bool(nlp.is_ironic))
                if nlp.primary_emotion:
                    emotions[nlp.primary_emotion] += 1
        n = len(events)
        behaviour: dict[str, Any] = {
            "posts_observed": n,
            "interaction_types": dict(kinds),
            "avg_likes_received": round(likes / n, 1),
            "avg_shares_received": round(shares / n, 1),
            "avg_replies_received": round(comments / n, 1),
        }
        if tags:
            behaviour["top_hashtags"] = [tag for tag, _ in tags.most_common(6)]
        if analysed:
            behaviour["sentiment_mix_pct"] = _pct(sentiments, analysed)
            behaviour["sarcasm_rate_pct"] = round(100 * ironic / analysed)
            if emotions:
                behaviour["top_emotions"] = [emo for emo, _ in emotions.most_common(3)]
        texts = [e.content_text.strip()[:TEXT_CHARS] for e, _ in events if e.content_text and e.content_text.strip()]
        profiles.append(ProfileIn(
            source=SOCIAL_SOURCE,
            external_ref=f"{user.platform}:{user.platform_user_id}",
            platform=user.platform,
            label=user.username or user.display_name,
            attributes=attributes,
            behaviour=behaviour,
            sample_texts=texts[:SAMPLE_TEXTS],
            weight=1.0,
        ))
    return profiles


def upsert_profiles(session: Session, profiles: list[ProfileIn], *, social_ids: dict[str, Any] | None = None) -> UpsertResult:
    existing = {
        (row.source, row.external_ref)
        for row in session.execute(
            select(AudienceProfile.source, AudienceProfile.external_ref).where(
                AudienceProfile.external_ref.in_([p.external_ref for p in profiles])
            )
        )
    }
    created = updated = 0
    for start in range(0, len(profiles), 500):
        chunk = profiles[start:start + 500]
        values = []
        for item in chunk:
            key = (item.source, item.external_ref)
            updated += key in existing
            created += key not in existing
            values.append({
                **item.model_dump(),
                "social_user_id": (social_ids or {}).get(item.external_ref),
            })
        stmt = insert(AudienceProfile).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_audience_profile_source_ref",
            set_={
                "platform": stmt.excluded.platform, "label": stmt.excluded.label,
                "attributes": stmt.excluded.attributes, "behaviour": stmt.excluded.behaviour,
                "sample_texts": stmt.excluded.sample_texts, "weight": stmt.excluded.weight,
                "social_user_id": stmt.excluded.social_user_id, "updated_at": func.now(),
            },
        )
        session.execute(stmt)
    session.commit()
    return UpsertResult(created=created, updated=updated, total_profiles=count_profiles(session), by_source=counts_by_source(session))


def sync_social_profiles(session: Session) -> UpsertResult:
    profiles = build_social_profiles(session)
    if not profiles:
        return UpsertResult(created=0, updated=0, total_profiles=count_profiles(session), by_source=counts_by_source(session))
    ids = {
        f"{platform}:{pid}": uid
        for uid, platform, pid in session.execute(select(SocialUser.user_id, SocialUser.platform, SocialUser.platform_user_id))
    }
    return upsert_profiles(session, profiles, social_ids=ids)


def count_profiles(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AudienceProfile)) or 0


def counts_by_source(session: Session) -> dict[str, int]:
    return dict(session.execute(select(AudienceProfile.source, func.count()).group_by(AudienceProfile.source)).all())


# ---------------------------------------------------------------------------
# Rendering for the model + evidence summaries
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k} {v}" for k, v in value.items())
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def profile_card(ref: str, profile: AudienceProfile, *, texts: int = 2) -> str:
    """Compact, schema-agnostic text card: every attribute key is rendered as-is."""
    parts = [ref]
    if profile.platform:
        parts.append(f"platform={profile.platform}")
    if profile.weight and profile.weight != 1:
        parts.append(f"represents≈{profile.weight:g} people")
    parts += [f"{k}={_fmt(v)[:160]}" for k, v in (profile.attributes or {}).items() if k != "platform"]
    parts += [f"{k}: {_fmt(v)[:160]}" for k, v in (profile.behaviour or {}).items()]
    for text in (profile.sample_texts or [])[:texts]:
        parts.append(f'post: "{text[:200]}"')
    return " | ".join(parts)


def attribute_breakdown(members: list[AudienceProfile], *, top: int = 5) -> dict[str, Any]:
    """Weighted distribution of every scalar attribute among members (generic, no fixed keys)."""
    weights = sum(m.weight or 1 for m in members) or 1
    counters: dict[str, Counter] = defaultdict(Counter)
    coverage: Counter = Counter()
    for member in members:
        w = member.weight or 1
        flat = dict(member.attributes or {})
        if member.platform:
            flat.setdefault("platform", member.platform)
        for key, value in flat.items():
            if isinstance(value, bool) or isinstance(value, str) and len(value) <= 60:
                counters[key][str(value)] += w
                coverage[key] += w
            elif isinstance(value, list):
                for item in value[:10]:
                    if isinstance(item, str) and len(item) <= 60:
                        counters[key][item] += w
                coverage[key] += w
    breakdown: dict[str, Any] = {}
    for key, counter in counters.items():
        if len(counter) > max(12, len(members) * 0.8) and len(members) > 5:
            continue  # near-unique free text (bios, names): not a useful distribution
        breakdown[key] = {
            "coverage_pct": round(100 * coverage[key] / weights),
            "top": [{"value": v, "pct": round(100 * c / weights)} for v, c in counter.most_common(top)],
        }
    return breakdown
