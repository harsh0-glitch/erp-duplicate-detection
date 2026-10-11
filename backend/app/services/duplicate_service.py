import math
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.duplicate import (
    DuplicateDetectionRun,
    DuplicateCandidate,
    DuplicateReview,
)
from app.schemas.duplicate import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateMatchItem,
    MatchedProductDetails,
    DuplicateReviewRequest,
    DuplicateReviewResponse,
    DuplicateDecisionResponse,
    DuplicateDetailResponse,
    DuplicateHistoryItem,
    DuplicateMatchHistoryItem,
    DuplicatePaginationMeta,
    DuplicateHistoryResponse,
)
from app.services.audit_service import AuditService
from app.ml.base import BaseDuplicateModel
from app.ml.placeholder import PlaceholderDuplicateModel

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Service orchestrating candidate retrieval, ML inference, and result tracking."""

    def __init__(
        self,
        db: Session,
        ml_model: Optional[BaseDuplicateModel] = None,
    ):
        self.db = db
        self.audit = AuditService(db)
        # If no custom ML model is injected, default to the safe development placeholder
        self.ml_model = ml_model if ml_model is not None else PlaceholderDuplicateModel()

    # -----------------------------------------------------------------------
    # Candidate Retrieval & Duplicate Check (Stage 6)
    # -----------------------------------------------------------------------

    def get_candidate_products(
        self,
        query: DuplicateCheckRequest,
        limit: int = 100,
    ) -> List[Product]:
        """Query candidate products from PostgreSQL using indexed attributes.
        
        Prioritizes candidates in the same category or brand to prune the search space
        across the ~85,000 product catalog before passing to the ML model.
        """
        stmt = select(Product).where(Product.is_active == True)

        # Exclude the query product itself if checking an existing catalog item
        if query.product_id is not None:
            stmt = stmt.where(Product.id != query.product_id)

        # Prioritize candidates sharing category or brand using indexes
        conditions = []
        if query.category:
            conditions.append(Product.category.ilike(query.category))
        if query.brand:
            conditions.append(Product.brand.ilike(query.brand))

        if conditions:
            stmt = stmt.where(or_(*conditions))

        stmt = stmt.order_by(Product.id.desc()).limit(limit)
        candidates = list(self.db.execute(stmt).scalars().all())

        # If not enough category/brand matches, fallback to broader active catalog
        if len(candidates) < 10:
            fallback_stmt = select(Product).where(Product.is_active == True)
            if query.product_id is not None:
                fallback_stmt = fallback_stmt.where(Product.id != query.product_id)
            fallback_stmt = fallback_stmt.order_by(Product.id.desc()).limit(limit)
            fallback_candidates = list(self.db.execute(fallback_stmt).scalars().all())

            # Combine candidates uniquely
            seen_ids = {c.id for c in candidates}
            for fc in fallback_candidates:
                if fc.id not in seen_ids and len(candidates) < limit:
                    candidates.append(fc)
                    seen_ids.add(fc.id)

        return candidates

    def check_duplicate(
        self,
        payload: DuplicateCheckRequest,
        threshold: float = 0.80,
        top_k: int = 5,
        record_history: bool = True,
    ) -> DuplicateCheckResponse:
        """Process a duplicate detection request.
        
        1. Validates input.
        2. Queries candidate products from PostgreSQL.
        3. If ML model is unavailable, logs a run and returns a clear status.
        4. If ML model is loaded, executes prediction, logs candidates, and returns matches.
        """
        start_time = time.perf_counter()

        # Step 1: Query candidate pool
        candidates = self.get_candidate_products(payload, limit=100)
        total_candidates = len(candidates)

        # Step 2: Check if ML model is ready for inference
        if not self.ml_model.is_available():
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            run_id = None

            if record_history:
                try:
                    run = DuplicateDetectionRun(
                        query_product_id=payload.product_id,
                        status="MODEL_UNAVAILABLE",
                        model_version=self.ml_model.get_model_version(),
                        total_candidates=total_candidates,
                        execution_time_ms=execution_time_ms,
                        run_metadata={
                            "query_sku": payload.sku,
                            "query_name": payload.name,
                            "input_product": payload.model_dump(),
                            "threshold": threshold,
                            "top_k": top_k,
                            "note": "ML model is under development; no inference performed.",
                        },
                        completed_at=datetime.now(timezone.utc),
                    )
                    self.db.add(run)
                    self.db.commit()
                    self.db.refresh(run)
                    run_id = run.id
                except Exception as exc:
                    self.db.rollback()
                    logger.warning(f"Could not record duplicate detection run: {exc}")

            self.audit.log_duplicate_checked(
                run_id=run_id,
                query_sku=payload.sku,
                query_name=payload.name,
                status="model_unavailable",
                model_version=self.ml_model.get_model_version(),
                total_candidates=total_candidates,
            )

            return DuplicateCheckResponse(
                status="model_unavailable",
                is_duplicate_detected=None,
                confidence_score=None,
                model_version=self.ml_model.get_model_version(),
                message="ML duplicate detection model is currently under development. The detection architecture is ready for model integration.",
                detection_run_id=run_id,
                total_candidates_analyzed=total_candidates,
                matches=[],
            )

        # Step 3: ML model is available -> Run prediction
        query_dict = payload.model_dump()
        candidate_dicts = [
            {
                "id": c.id,
                "sku": c.sku,
                "name": c.name,
                "brand": c.brand,
                "category": c.category,
                "subcategory": c.subcategory,
                "unit": c.unit,
                "attributes": c.attributes,
                "is_active": c.is_active,
            }
            for c in candidates
        ]

        is_duplicate, confidence, raw_matches = self.ml_model.predict(
            query_product=query_dict,
            candidate_pool=candidate_dicts,
            threshold=threshold,
            top_k=top_k,
        )

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        run_id = None

        if record_history:
            try:
                run = DuplicateDetectionRun(
                    query_product_id=payload.product_id,
                    status="COMPLETED",
                    model_version=self.ml_model.get_model_version(),
                    total_candidates=total_candidates,
                    execution_time_ms=execution_time_ms,
                    run_metadata={
                        "query_sku": payload.sku,
                        "query_name": payload.name,
                        "input_product": payload.model_dump(),
                        "threshold": threshold,
                        "top_k": top_k,
                    },
                    completed_at=datetime.now(timezone.utc),
                )
                self.db.add(run)
                self.db.commit()
                self.db.refresh(run)
                run_id = run.id

                # Persist candidates
                for match_data in raw_matches:
                    cand = DuplicateCandidate(
                        run_id=run.id,
                        query_product_id=payload.product_id,
                        matched_product_id=match_data["matched_product_id"],
                        similarity_score=match_data["similarity_score"],
                        confidence_score=match_data.get("confidence_score"),
                        matching_features=match_data.get("matching_features", {}),
                        rank=match_data["rank"],
                    )
                    self.db.add(cand)
                self.db.commit()
            except Exception as exc:
                self.db.rollback()
                logger.error(f"Error persisting duplicate detection run/candidates: {exc}")

        # Assemble match response items
        candidate_map = {c.id: c for c in candidates}
        match_items: List[DuplicateMatchItem] = []

        for m in raw_matches:
            matched_prod = candidate_map.get(m["matched_product_id"])
            prod_details = None
            if matched_prod:
                prod_details = MatchedProductDetails.model_validate(matched_prod)

            match_items.append(
                DuplicateMatchItem(
                    matched_product_id=m["matched_product_id"],
                    similarity_score=m["similarity_score"],
                    confidence_score=m.get("confidence_score"),
                    rank=m["rank"],
                    matching_features=m.get("matching_features", {}),
                    matched_product=prod_details,
                )
            )

        self.audit.log_duplicate_checked(
            run_id=run_id,
            query_sku=payload.sku,
            query_name=payload.name,
            status="completed",
            model_version=self.ml_model.get_model_version(),
            total_candidates=total_candidates,
        )

        return DuplicateCheckResponse(
            status="completed",
            is_duplicate_detected=is_duplicate,
            confidence_score=confidence,
            model_version=self.ml_model.get_model_version(),
            message="Duplicate detection completed successfully.",
            detection_run_id=run_id,
            total_candidates_analyzed=total_candidates,
            matches=match_items,
        )

    # -----------------------------------------------------------------------
    # Confirm & Reject Reviews (Stage 7)
    # -----------------------------------------------------------------------

    def review_duplicate(
        self,
        duplicate_id: int,
        decision: str,  # "CONFIRMED" or "REJECTED"
        payload: Optional[DuplicateReviewRequest] = None,
    ) -> DuplicateDecisionResponse:
        """Confirm or reject a candidate duplicate match.
        
        Stores user decision, optional reason/notes, reviewer ID, and timestamps.
        If duplicate_id matches a candidate directly, it updates that candidate.
        If duplicate_id matches a detection run with candidates, it updates the run's primary candidate.
        """
        payload = payload or DuplicateReviewRequest()

        # Step 1: Resolve the candidate match
        candidate = self.db.get(DuplicateCandidate, duplicate_id)
        if candidate is None:
            # Check if duplicate_id is a detection run ID with candidates
            run = self.db.get(DuplicateDetectionRun, duplicate_id)
            if run is not None:
                if run.candidates:
                    candidate = run.candidates[0]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate detection run {duplicate_id} has no candidate matches to review.",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Duplicate record with ID {duplicate_id} not found.",
                )

        # Step 2: Fetch or create DuplicateReview
        review_stmt = select(DuplicateReview).where(DuplicateReview.candidate_id == candidate.id)
        review = self.db.execute(review_stmt).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if review is not None:
            review.decision = decision
            if payload.reason is not None:
                review.reason = payload.reason
            if payload.reviewer_id is not None:
                review.reviewer_id = payload.reviewer_id
            review.updated_at = now
        else:
            review = DuplicateReview(
                candidate_id=candidate.id,
                decision=decision,
                reason=payload.reason,
                reviewer_id=payload.reviewer_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(review)

        self.db.commit()
        self.db.refresh(review)
        if review.id is None:
            review.id = getattr(candidate, "id", 1)

        action_text = "confirmed" if decision == "CONFIRMED" else "rejected"
        self.audit.log_duplicate_review(
            candidate_id=candidate.id,
            decision=decision,
            reason=payload.reason,
            reviewer_id=payload.reviewer_id,
        )
        return DuplicateDecisionResponse(
            message=f"Duplicate match {candidate.id} {action_text} successfully.",
            duplicate_id=candidate.id,
            decision=decision,
            review=DuplicateReviewResponse.model_validate(review),
        )

    def confirm_duplicate(
        self,
        duplicate_id: int,
        payload: Optional[DuplicateReviewRequest] = None,
    ) -> DuplicateDecisionResponse:
        """Record a CONFIRMED duplicate decision."""
        return self.review_duplicate(
            duplicate_id=duplicate_id,
            decision="CONFIRMED",
            payload=payload,
        )

    def reject_duplicate(
        self,
        duplicate_id: int,
        payload: Optional[DuplicateReviewRequest] = None,
    ) -> DuplicateDecisionResponse:
        """Record a REJECTED duplicate decision."""
        return self.review_duplicate(
            duplicate_id=duplicate_id,
            decision="REJECTED",
            payload=payload,
        )

    # -----------------------------------------------------------------------
    # Duplicate Details & History (Stage 7)
    # -----------------------------------------------------------------------

    def get_duplicate(self, duplicate_id: int) -> DuplicateDetailResponse:
        """Retrieve complete details of a duplicate candidate or detection run."""
        # 1. Check if duplicate_id is a candidate
        candidate = self.db.get(DuplicateCandidate, duplicate_id)
        if candidate is not None:
            run = candidate.run

            query_prod_dict = None
            if candidate.query_product:
                query_prod_dict = {
                    "id": candidate.query_product.id,
                    "sku": candidate.query_product.sku,
                    "name": candidate.query_product.name,
                    "brand": candidate.query_product.brand,
                    "category": candidate.query_product.category,
                    "subcategory": candidate.query_product.subcategory,
                    "unit": candidate.query_product.unit,
                    "attributes": candidate.query_product.attributes,
                    "is_active": candidate.query_product.is_active,
                }
            elif run and run.run_metadata.get("input_product"):
                query_prod_dict = run.run_metadata.get("input_product")

            matched_prod_dict = None
            if candidate.matched_product:
                matched_prod_dict = {
                    "id": candidate.matched_product.id,
                    "sku": candidate.matched_product.sku,
                    "name": candidate.matched_product.name,
                    "brand": candidate.matched_product.brand,
                    "category": candidate.matched_product.category,
                    "subcategory": candidate.matched_product.subcategory,
                    "unit": candidate.matched_product.unit,
                    "attributes": candidate.matched_product.attributes,
                    "is_active": candidate.matched_product.is_active,
                }

            review_resp = None
            review_status = "PENDING"
            if candidate.review:
                review_resp = DuplicateReviewResponse.model_validate(candidate.review)
                review_status = candidate.review.decision

            return DuplicateDetailResponse(
                id=candidate.id,
                record_type="candidate",
                run_id=candidate.run_id,
                status=review_status,
                model_version=run.model_version if run else None,
                similarity_score=candidate.similarity_score,
                confidence_score=candidate.confidence_score,
                rank=candidate.rank,
                matching_features=candidate.matching_features or {},
                created_at=candidate.created_at,
                query_product=query_prod_dict,
                matched_product=matched_prod_dict,
                review=review_resp,
                review_status=review_status,
                matches=[],
            )

        # 2. Check if duplicate_id is a detection run
        run = self.db.get(DuplicateDetectionRun, duplicate_id)
        if run is not None:
            query_prod_dict = None
            if run.query_product:
                query_prod_dict = {
                    "id": run.query_product.id,
                    "sku": run.query_product.sku,
                    "name": run.query_product.name,
                    "brand": run.query_product.brand,
                    "category": run.query_product.category,
                    "subcategory": run.query_product.subcategory,
                    "unit": run.query_product.unit,
                    "attributes": run.query_product.attributes,
                    "is_active": run.query_product.is_active,
                }
            elif run.run_metadata.get("input_product"):
                query_prod_dict = run.run_metadata.get("input_product")

            match_items = []
            for c in run.candidates:
                match_items.append(
                    DuplicateMatchHistoryItem(
                        id=c.id,
                        matched_product_id=c.matched_product_id,
                        matched_product_sku=c.matched_product.sku if c.matched_product else None,
                        matched_product_name=c.matched_product.name if c.matched_product else None,
                        similarity_score=c.similarity_score,
                        confidence_score=c.confidence_score,
                        rank=c.rank,
                        matching_features=c.matching_features or {},
                        review_status=c.review.decision if c.review else "PENDING",
                        review_decision=c.review.decision if c.review else None,
                        reviewed_at=c.review.updated_at if c.review else None,
                        reviewer_id=c.review.reviewer_id if c.review else None,
                    )
                )

            return DuplicateDetailResponse(
                id=run.id,
                record_type="detection_run",
                run_id=run.id,
                status=run.status,
                model_version=run.model_version,
                similarity_score=None,
                confidence_score=None,
                rank=None,
                matching_features=run.run_metadata or {},
                created_at=run.created_at,
                query_product=query_prod_dict,
                matched_product=None,
                review=None,
                review_status="PENDING",
                matches=match_items,
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Duplicate record with ID {duplicate_id} not found.",
        )

    def get_history(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        decision_filter: Optional[str] = None,
        query_product_id: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> DuplicateHistoryResponse:
        """List paginated duplicate detection history with optional filters."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        stmt = select(DuplicateDetectionRun)

        # Apply run status filter (e.g. COMPLETED, MODEL_UNAVAILABLE)
        if status_filter:
            stmt = stmt.where(DuplicateDetectionRun.status == status_filter)

        # Apply query product filter
        if query_product_id is not None:
            stmt = stmt.where(DuplicateDetectionRun.query_product_id == query_product_id)

        # Filter by review decision (CONFIRMED, REJECTED, PENDING)
        if decision_filter:
            dec = decision_filter.upper()
            if dec in ("CONFIRMED", "REJECTED"):
                stmt = (
                    stmt.join(DuplicateDetectionRun.candidates)
                    .join(DuplicateCandidate.review)
                    .where(DuplicateReview.decision == dec)
                )
            elif dec == "PENDING":
                stmt = (
                    stmt.join(DuplicateDetectionRun.candidates)
                    .outerjoin(DuplicateCandidate.review)
                    .where(DuplicateReview.id.is_(None))
                )

        # Filter by minimum similarity score
        if min_similarity is not None:
            stmt = stmt.join(DuplicateDetectionRun.candidates).where(
                DuplicateCandidate.similarity_score >= min_similarity
            )

        stmt = stmt.distinct()

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(DuplicateDetectionRun.id.desc()).offset(offset).limit(page_size)
        runs = list(self.db.execute(stmt).scalars().all())

        items: List[DuplicateHistoryItem] = []
        for r in runs:
            # Query product details
            input_prod = r.run_metadata.get("input_product") or {}
            query_sku = r.run_metadata.get("query_sku")
            query_name = r.run_metadata.get("query_name")

            if r.query_product:
                query_sku = query_sku or r.query_product.sku
                query_name = query_name or r.query_product.name
                if not input_prod:
                    input_prod = {
                        "id": r.query_product.id,
                        "sku": r.query_product.sku,
                        "name": r.query_product.name,
                        "brand": r.query_product.brand,
                        "category": r.query_product.category,
                    }

            match_items: List[DuplicateMatchHistoryItem] = []
            for c in r.candidates:
                match_items.append(
                    DuplicateMatchHistoryItem(
                        id=c.id,
                        matched_product_id=c.matched_product_id,
                        matched_product_sku=c.matched_product.sku if c.matched_product else None,
                        matched_product_name=c.matched_product.name if c.matched_product else None,
                        similarity_score=c.similarity_score,
                        confidence_score=c.confidence_score,
                        rank=c.rank,
                        matching_features=c.matching_features or {},
                        review_status=c.review.decision if c.review else "PENDING",
                        review_decision=c.review.decision if c.review else None,
                        reviewed_at=c.review.updated_at if c.review else None,
                        reviewer_id=c.review.reviewer_id if c.review else None,
                    )
                )

            items.append(
                DuplicateHistoryItem(
                    id=r.id,
                    status=r.status,
                    model_version=r.model_version,
                    query_product_id=r.query_product_id,
                    query_product_sku=query_sku,
                    query_product_name=query_name,
                    input_product=input_prod,
                    total_candidates_analyzed=r.total_candidates,
                    execution_time_ms=r.execution_time_ms,
                    created_at=r.created_at,
                    completed_at=r.completed_at,
                    matches=match_items,
                )
            )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return DuplicateHistoryResponse(
            items=items,
            pagination=DuplicatePaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )
