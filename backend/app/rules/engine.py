"""规则引擎

纯内存的规则评估，输入申请全量资料，输出流转决策。
设计：条件 JSON 中任一子条件命中即触发规则；结论类动作按严重度取最严重；
拒保/延期直接生效，其余按 体检 > 转人工 > 自动结论 的顺序流转。
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.models.underwriting import ACTION_SEVERITY, UnderwritingRule


@dataclass
class RuleHit:
    """单条规则命中信息"""

    rule: UnderwritingRule
    matched_by: str  # 命中的子条件说明，用于留痕


@dataclass
class Decision:
    """评估决策：next_status 为申请单下一状态，conclusion 为需自动出具的结论"""

    next_status: str
    conclusion: dict | None = None  # 结论类决策时携带，含 result_type/reason/extra_rate 等
    hits: list = field(default_factory=list)  # 全部命中规则


def _age(birth_date: date) -> int:
    """按出生日期计算周岁"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _rule_matches(rule: UnderwritingRule, ctx: dict) -> str | None:
    """判断单条规则是否命中，命中返回子条件说明，未命中返回 None。

    ctx 包含：risk_question_ids（答"是"的 yes_no 题）、disease_names、
    family_names、age、coverage_amount。
    """
    cond = rule.condition_json or {}

    qids = cond.get("question_ids") or []
    if qids and any(q in ctx["risk_question_ids"] for q in qids):
        return "健康告知风险题"

    for kw in cond.get("disease_keywords") or []:
        if any(kw in name for name in ctx["disease_names"]):
            return f"既往病史关键词：{kw}"
    for kw in cond.get("family_keywords") or []:
        if any(kw in name for name in ctx["family_names"]):
            return f"家族病史关键词：{kw}"

    age = ctx["age"]
    if cond.get("min_age") is not None and age >= cond["min_age"]:
        return f"年龄≥{cond['min_age']}"
    if cond.get("max_age") is not None and age <= cond["max_age"]:
        return f"年龄≤{cond['max_age']}"

    amount = ctx["coverage_amount"]
    if cond.get("min_amount") is not None and Decimal(str(cond["min_amount"])) <= amount:
        return f"保额≥{cond['min_amount']}"
    return None


def evaluate(rules: list[UnderwritingRule], ctx: dict, skip_exam: bool = False) -> Decision:
    """评估入口：返回申请单下一状态与（可选的）自动结论。

    skip_exam=True 用于体检结果回流后的重评：体检类规则已完成使命，不再触发，
    避免"年龄达标要求体检"类规则在体检后再次要求体检造成循环。
    """
    hits = []
    for rule in rules:
        if skip_exam and rule.action == "EXAM":
            continue
        matched_by = _rule_matches(rule, ctx)
        if matched_by is not None:
            hits.append(RuleHit(rule=rule, matched_by=matched_by))

    conclusions = [h for h in hits if h.rule.action in ACTION_SEVERITY]
    # 最严重结论（DECLINE > POSTPONE > EXCLUSION > EXTRA > STANDARD）
    worst = max(conclusions, key=lambda h: ACTION_SEVERITY[h.rule.action], default=None)
    need_exam = any(h.rule.action == "EXAM" for h in hits)
    need_manual = any(h.rule.action == "MANUAL" for h in hits)

    # 拒保/延期无需补充资料，直接出结论
    if worst and worst.rule.action in ("DECLINE", "POSTPONE"):
        return Decision(next_status="DECIDED", conclusion=_build_conclusion(worst), hits=hits)
    # 需体检的案件先走体检，体检结果回来后再评估（M5 闭环）
    if need_exam:
        return Decision(next_status="EXAM_REQUIRED", hits=hits)
    if need_manual:
        return Decision(next_status="MANUAL_REQUIRED", hits=hits)
    if worst:
        return Decision(next_status="DECIDED", conclusion=_build_conclusion(worst), hits=hits)
    # 无任何规则命中：默认标体承保
    return Decision(
        next_status="DECIDED",
        conclusion={"result_type": "STANDARD", "reason": "告知内容无异常，按标准体承保",
                    "extra_rate": None, "exclusion_desc": None, "postpone_months": None},
        hits=[],
    )


def _build_conclusion(hit: RuleHit) -> dict:
    """由命中的最严重规则构造自动结论"""
    rule = hit.rule
    reasons = [f"命中规则《{rule.rule_name}》（{hit.matched_by}）"]
    return {
        "result_type": rule.action,
        "reason": "；".join(reasons),
        "extra_rate": rule.extra_rate if rule.action == "EXTRA" else None,
        "exclusion_desc": rule.exclusion_desc if rule.action == "EXCLUSION" else None,
        "postpone_months": rule.postpone_months if rule.action == "POSTPONE" else None,
    }
