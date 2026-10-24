"""智能核保评估服务

提交申请后触发：加载申请全量资料 -> 规则引擎评估 -> 按决策流转状态并出具自动结论。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationAnswer, FamilyHistory, MedicalHistory
from app.models.underwriting import UnderwritingResult, UnderwritingRule
from app.models.product import DisclosureQuestion
from app.rules import engine


def _load_context(db: Session, app: Application) -> dict:
    """汇总规则评估所需的申请上下文。"""
    answers = db.execute(
        select(ApplicationAnswer).where(ApplicationAnswer.application_id == app.id)
    ).scalar_one_or_none()
    answer_list = answers.answers if answers else []

    # 答"是"的 yes_no 题即为风险告知
    risk_question_ids = set()
    if answer_list:
        qids = [a["question_id"] for a in answer_list]
        q_rows = db.execute(
            select(DisclosureQuestion.id).where(
                DisclosureQuestion.id.in_(qids), DisclosureQuestion.answer_type == "yes_no"
            )
        ).scalars().all()
        yes_no_ids = set(q_rows)
        risk_question_ids = {a["question_id"] for a in answer_list
                             if a["question_id"] in yes_no_ids and a["answer"] == "yes"}

    disease_names = [h.disease_name for h in db.execute(
        select(MedicalHistory).where(MedicalHistory.application_id == app.id)).scalars()]
    family_names = [h.disease_name for h in db.execute(
        select(FamilyHistory).where(FamilyHistory.application_id == app.id)).scalars()]

    return {
        "risk_question_ids": risk_question_ids,
        "disease_names": disease_names,
        "family_names": family_names,
        "age": engine._age(app.birth_date),
        "coverage_amount": app.coverage_amount,
    }


def run_auto_underwriting(db: Session, app_id: int, from_exam: bool = False) -> None:
    """对指定申请执行智能核保评估并流转状态。

    幂等约定：仅处理处于 AUTO_UNDERWRITING 状态的申请，重复调用不产生副作用。
    from_exam=True 表示体检结果回流后的重评，跳过体检类规则避免循环要求体检。
    """
    app = db.get(Application, app_id)
    if app is None or app.status != "AUTO_UNDERWRITING":
        return

    rules = db.execute(
        select(UnderwritingRule).where(
            UnderwritingRule.status == 1,
            (UnderwritingRule.product_id.is_(None)) | (UnderwritingRule.product_id == app.product_id),
        )
    ).scalars().all()

    decision = engine.evaluate(rules, _load_context(db, app), skip_exam=from_exam)

    # 无论是否出具自动结论，都保留评估快照：转人工/体检时供核保员参考命中规则
    app.auto_advice = {
        "next_status": decision.next_status,
        "hits": [{"rule_id": h.rule.id, "rule_name": h.rule.rule_name,
                  "action": h.rule.action, "matched_by": h.matched_by}
                 for h in decision.hits],
    }

    if decision.conclusion is not None:
        db.add(UnderwritingResult(
            application_id=app.id,
            result_type=decision.conclusion["result_type"],
            reason=decision.conclusion["reason"],
            extra_rate=decision.conclusion["extra_rate"],
            exclusion_desc=decision.conclusion["exclusion_desc"],
            postpone_months=decision.conclusion["postpone_months"],
            source="AUTO",
            decided_by=None,
            hit_rules=[{"rule_id": h.rule.id, "rule_name": h.rule.rule_name,
                        "action": h.rule.action, "matched_by": h.matched_by}
                       for h in decision.hits],
            review_status="NONE",
            is_final=1,
        ))
    app.status = decision.next_status
    db.commit()
