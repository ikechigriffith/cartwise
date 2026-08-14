import json
from sqlalchemy import select

from app.db import SessionLocal
from app.models import StoreCandidate
from app.schemas.store_review import CandidateResolutionRequest
from app.services.store_review import link_candidate_to_existing_store, suggest_existing_stores


def auto_link_candidates(min_score: float = 0.70) -> dict[str, int]:
    auto_linked = 0
    total_backfilled_obs = 0
    skipped = 0

    with SessionLocal() as session:
        candidates = list(
            session.scalars(
                select(StoreCandidate).where(StoreCandidate.status == "needs_review")
            ).all()
        )

        for candidate in candidates:
            suggestions = suggest_existing_stores(session, candidate, limit=1)
            if not suggestions:
                skipped += 1
                continue

            best = suggestions[0]
            if best["score"] >= min_score:
                request = CandidateResolutionRequest(
                    store_id=best["store_id"],
                    notes=f"Auto-linked with confidence score {best['score']} ({', '.join(best['reasons'])})",
                    fields_changed={"auto_score": best["score"], "reasons": best["reasons"]},
                )
                review = link_candidate_to_existing_store(session, candidate.id, request)
                auto_linked += 1
                total_backfilled_obs += review.observations_backfilled
            else:
                skipped += 1

    return {
        "candidates_evaluated": len(candidates),
        "candidates_auto_linked": auto_linked,
        "observations_backfilled": total_backfilled_obs,
        "remaining_needs_review": skipped,
    }


if __name__ == "__main__":
    result = auto_link_candidates()
    print(json.dumps(result, indent=2))
