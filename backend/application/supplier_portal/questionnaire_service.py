"""M35 Questionnaire Engine Service.

Manages questionnaire templates, assignments, and supplier responses.

Internal:
  create_template()         — define a new questionnaire blueprint
  add_question()            — add a question to a template
  assign_questionnaire()    — send template to supplier
  review_assignment()       — approve / reject submitted questionnaire
  list_assignments()        — list by org / supplier / status

Supplier:
  get_my_assignments()      — supplier sees only their own
  save_answer()             — upsert one answer (autosave)
  submit_questionnaire()    — transition to 'submitted'

Built-in templates:
  seed_builtin_templates()  — idempotent seed (called at startup)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def _log_activity(
    supplier_id: str,
    supplier_user_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    session,
    metadata: dict | None = None,
) -> None:
    import json

    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    now = datetime.now(UTC)
    model = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("questionnaire_activity_log_failed", error=str(exc))


_BUILTIN_TEMPLATES = [
    {
        "name": "Supplier ESG Assessment",
        "description": "Comprehensive ESG assessment covering environmental, social, and governance dimensions.",
        "version": "1.0",
        "questions": [
            {"text": "Does your organisation have a formal ESG policy?", "type": "boolean"},
            {"text": "Describe your environmental management system.", "type": "text"},
            {"text": "How many work-related injuries occurred last year?", "type": "number"},
            {
                "text": "Select your primary environmental certifications.",
                "type": "multi_select",
                "options": ["ISO 14001", "ISO 45001", "EMAS", "None"],
            },
        ],
    },
    {
        "name": "Human Rights Due Diligence",
        "description": "Assesses supplier compliance with human rights obligations under LkSG/CSDDD.",
        "version": "1.0",
        "questions": [
            {"text": "Do you have a human rights policy?", "type": "boolean"},
            {"text": "Describe your grievance mechanism.", "type": "text"},
            {"text": "Upload your latest human rights audit report.", "type": "file_upload"},
        ],
    },
    {
        "name": "Modern Slavery",
        "description": "Modern Slavery Act compliance questionnaire.",
        "version": "1.0",
        "questions": [
            {
                "text": "Does your organisation conduct modern slavery risk assessments?",
                "type": "boolean",
            },
            {
                "text": "Describe the steps taken to address modern slavery in supply chains.",
                "type": "text",
            },
        ],
    },
    {
        "name": "Environmental Compliance",
        "description": "Environmental regulatory compliance check.",
        "version": "1.0",
        "questions": [
            {"text": "What is your annual Scope 1 CO₂ emission (tonnes)?", "type": "number"},
            {"text": "What is your annual Scope 2 CO₂ emission (tonnes)?", "type": "number"},
            {"text": "Do you have a net-zero target?", "type": "boolean"},
            {"text": "Upload environmental compliance certificates.", "type": "file_upload"},
        ],
    },
    {
        "name": "Governance Controls",
        "description": "Corporate governance and anti-corruption controls assessment.",
        "version": "1.0",
        "questions": [
            {"text": "Is there an independent audit committee?", "type": "boolean"},
            {"text": "Describe your anti-bribery and corruption policy.", "type": "text"},
            {
                "text": "Has your organisation been subject to regulatory action in the last 3 years?",
                "type": "boolean",
            },
        ],
    },
    {
        "name": "CSRD Readiness",
        "description": "Corporate Sustainability Reporting Directive readiness assessment.",
        "version": "1.0",
        "questions": [
            {"text": "Have you performed a double materiality assessment?", "type": "boolean"},
            {
                "text": "Which ESRS standards are you currently reporting against?",
                "type": "multi_select",
                "options": ["E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1", "None"],
            },
            {"text": "When do you expect full CSRD compliance?", "type": "text"},
        ],
    },
    {
        "name": "LkSG Supplier Review",
        "description": "German Supply Chain Due Diligence Act (LkSG) review.",
        "version": "1.0",
        "questions": [
            {
                "text": "Have you identified human rights and environmental risks per LkSG?",
                "type": "boolean",
            },
            {"text": "Do you have a complaints mechanism per §8 LkSG?", "type": "boolean"},
            {"text": "Upload your most recent LkSG risk analysis.", "type": "file_upload"},
        ],
    },
]


async def seed_builtin_templates(session) -> None:
    """Seed the built-in questionnaire templates.  Idempotent — skips existing."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import (
        QuestionnaireQuestionModel,
        QuestionnaireTemplateModel,
    )

    now = datetime.now(UTC)
    for tmpl in _BUILTIN_TEMPLATES:
        stmt = select(QuestionnaireTemplateModel).where(
            QuestionnaireTemplateModel.name == tmpl["name"],
            QuestionnaireTemplateModel.template_version == tmpl["version"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        template_id = str(uuid.uuid4())
        questions = tmpl.get("questions", [])
        template_model = QuestionnaireTemplateModel(
            id=template_id,
            name=tmpl["name"],
            template_version=tmpl["version"],
            description=tmpl["description"],
            is_active=True,
            created_by_user_id="system",
            question_count=len(questions),
            created_at=now,
            updated_at=now,
        )
        session.add(template_model)
        for i, q in enumerate(questions):
            q_model = QuestionnaireQuestionModel(
                id=str(uuid.uuid4()),
                template_id=template_id,
                order=i,
                text=q["text"],
                question_type=q["type"],
                options_json=json.dumps(q.get("options", [])),
                required=True,
                weight=1.0,
                created_at=now,
                updated_at=now,
            )
            session.add(q_model)

    try:
        await session.flush()
    except Exception as exc:
        logger.warning("questionnaire_seed_failed", error=str(exc))


async def create_template(
    name: str,
    description: str,
    created_by_user_id: str,
    template_version: str = "1.0",
    session=None,
) -> object:
    from infrastructure.persistence.models.supplier_portal import QuestionnaireTemplateModel

    now = datetime.now(UTC)
    model = QuestionnaireTemplateModel(
        id=str(uuid.uuid4()),
        name=name,
        template_version=template_version,
        description=description,
        is_active=True,
        created_by_user_id=created_by_user_id,
        question_count=0,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()
    return model


async def add_question(
    template_id: str,
    text: str,
    question_type: str,
    order: int,
    options: list | None = None,
    required: bool = True,
    weight: float = 1.0,
    session=None,
) -> object:

    from infrastructure.persistence.models.supplier_portal import (
        QuestionnaireQuestionModel,
        QuestionnaireTemplateModel,
    )

    now = datetime.now(UTC)
    q = QuestionnaireQuestionModel(
        id=str(uuid.uuid4()),
        template_id=template_id,
        order=order,
        text=text,
        question_type=question_type,
        options_json=json.dumps(options or []),
        required=required,
        weight=weight,
        created_at=now,
        updated_at=now,
    )
    session.add(q)

    # Update question count on template
    from sqlalchemy import update

    await session.execute(
        update(QuestionnaireTemplateModel)
        .where(QuestionnaireTemplateModel.id == template_id)
        .values(question_count=QuestionnaireTemplateModel.question_count + 1, updated_at=now)
    )
    await session.flush()
    return q


async def assign_questionnaire(
    template_id: str,
    supplier_id: str,
    organization_id: str,
    assigned_by_user_id: str,
    due_date: datetime | None = None,
    session=None,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import (
        QuestionnaireAssignmentModel,
        QuestionnaireTemplateModel,
    )

    # Load template to capture version
    tmpl_stmt = select(QuestionnaireTemplateModel).where(
        QuestionnaireTemplateModel.id == template_id
    )
    tmpl = (await session.execute(tmpl_stmt)).scalar_one_or_none()
    if tmpl is None:
        raise ValueError(f"Questionnaire template {template_id!r} not found")

    now = datetime.now(UTC)
    assignment = QuestionnaireAssignmentModel(
        id=str(uuid.uuid4()),
        template_id=template_id,
        template_version=tmpl.template_version,
        supplier_id=supplier_id,
        organization_id=organization_id,
        assigned_by_user_id=assigned_by_user_id,
        questionnaire_status="assigned",
        due_date=due_date,
        assigned_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(assignment)
    await session.flush()
    logger.info(
        "questionnaire_assigned",
        assignment_id=assignment.id,
        supplier_id=supplier_id,
        template_id=template_id,
    )
    return assignment


async def get_my_assignments(
    supplier_id: str,
    status: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import QuestionnaireAssignmentModel

    stmt = select(QuestionnaireAssignmentModel).where(
        QuestionnaireAssignmentModel.supplier_id == supplier_id
    )
    if status:
        stmt = stmt.where(QuestionnaireAssignmentModel.questionnaire_status == status)
    stmt = stmt.order_by(QuestionnaireAssignmentModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def save_answer(
    assignment_id: str,
    question_id: str,
    supplier_user_id: str,
    supplier_id: str,
    answer_text: str = "",
    answer_json: str = "null",
    file_path: str | None = None,
    session=None,
) -> object:
    """Upsert an answer for a question in an assignment (autosave)."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import (
        QuestionnaireAnswerModel,
        QuestionnaireAssignmentModel,
        QuestionnaireQuestionModel,
    )

    # Guard: assignment must belong to this supplier
    a_stmt = select(QuestionnaireAssignmentModel).where(
        QuestionnaireAssignmentModel.id == assignment_id,
        QuestionnaireAssignmentModel.supplier_id == supplier_id,
    )
    assignment = (await session.execute(a_stmt)).scalar_one_or_none()
    if assignment is None:
        raise ValueError("Assignment not found or does not belong to this supplier")
    if assignment.questionnaire_status not in ("assigned", "in_progress"):
        raise ValueError("Cannot edit answers for this assignment status")

    # F9: validate question belongs to this assignment's template
    q_stmt = select(QuestionnaireQuestionModel).where(
        QuestionnaireQuestionModel.id == question_id,
        QuestionnaireQuestionModel.template_id == assignment.template_id,
    )
    question = (await session.execute(q_stmt)).scalar_one_or_none()
    if question is None:
        raise ValueError("Question does not belong to this questionnaire's template")

    existing_stmt = select(QuestionnaireAnswerModel).where(
        QuestionnaireAnswerModel.assignment_id == assignment_id,
        QuestionnaireAnswerModel.question_id == question_id,
    )
    now = datetime.now(UTC)
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        existing.answer_text = answer_text
        existing.answer_json = answer_json
        existing.file_path = file_path
        existing.answered_by_supplier_user_id = supplier_user_id
        existing.answered_at = now
        existing.updated_at = now
        await session.flush()
        return existing

    answer = QuestionnaireAnswerModel(
        id=str(uuid.uuid4()),
        assignment_id=assignment_id,
        question_id=question_id,
        answer_text=answer_text,
        answer_json=answer_json,
        file_path=file_path,
        answered_by_supplier_user_id=supplier_user_id,
        answered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(answer)

    # Transition to in_progress on first answer
    if assignment.questionnaire_status == "assigned":
        assignment.questionnaire_status = "in_progress"
        assignment.updated_at = now

    await session.flush()
    return answer


async def submit_questionnaire(
    assignment_id: str,
    supplier_id: str,
    supplier_user_id: str | None = None,
    session=None,
) -> object:
    """F5: logs activity event on submission."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import QuestionnaireAssignmentModel

    stmt = select(QuestionnaireAssignmentModel).where(
        QuestionnaireAssignmentModel.id == assignment_id,
        QuestionnaireAssignmentModel.supplier_id == supplier_id,
    )
    assignment = (await session.execute(stmt)).scalar_one_or_none()
    if assignment is None:
        raise ValueError("Assignment not found")
    if assignment.questionnaire_status not in ("assigned", "in_progress"):
        raise ValueError(f"Cannot submit assignment in status: {assignment.questionnaire_status}")

    now = datetime.now(UTC)
    assignment.questionnaire_status = "submitted"
    assignment.submitted_at = now
    assignment.updated_at = now
    await session.flush()

    await _log_activity(
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type="questionnaire_submitted",
        entity_type="questionnaire_assignment",
        entity_id=assignment_id,
        session=session,
    )
    return assignment


async def review_assignment(
    assignment_id: str,
    organization_id: str,
    reviewed_by: str,
    new_status: str,
    reviewer_comments: str = "",
    score: float | None = None,
    session=None,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import QuestionnaireAssignmentModel

    _VALID = {"approved", "rejected"}
    if new_status not in _VALID:
        raise ValueError(f"Invalid review status. Must be one of: {_VALID}")

    # F3: SELECT FOR UPDATE to serialize concurrent reviewers
    stmt = (
        select(QuestionnaireAssignmentModel)
        .where(
            QuestionnaireAssignmentModel.id == assignment_id,
            QuestionnaireAssignmentModel.organization_id == organization_id,
            QuestionnaireAssignmentModel.questionnaire_status == "submitted",
        )
        .with_for_update()
    )
    assignment = (await session.execute(stmt)).scalar_one_or_none()
    if assignment is None:
        raise ValueError("Assignment not found, not submitted, or not in your organisation")

    now = datetime.now(UTC)
    assignment.questionnaire_status = new_status
    assignment.reviewed_by = reviewed_by
    assignment.reviewed_at = now
    assignment.reviewer_comments = reviewer_comments
    assignment.score = score
    assignment.updated_at = now
    await session.flush()

    # F5: activity audit
    await _log_activity(
        supplier_id=assignment.supplier_id,
        supplier_user_id=None,
        event_type=f"questionnaire_{new_status}",
        entity_type="questionnaire_assignment",
        entity_id=assignment_id,
        metadata={"reviewed_by": reviewed_by},
        session=session,
    )
    return assignment
