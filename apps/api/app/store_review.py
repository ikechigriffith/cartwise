"""Compatibility wrapper for store review service.

New code should import from app.services.store_review and app.schemas.store_review.
"""
from app.schemas.store_review import CandidateResolutionRequest, CreateStoreFromCandidateRequest
from app.services.store_review import *  # noqa: F401,F403
