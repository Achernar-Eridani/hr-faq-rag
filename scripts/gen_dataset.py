import argparse
import csv
import os
import random
from dataclasses import dataclass
from typing import List, Dict

# --- 1. 定义数据结构 ---
# 使用 dataclass 是为了让代码更规范，比用字典（dict）更不容易写错字段名
@dataclass
class FAQ:
    faq_id: str
    title: str
    question: str
    answer: str
    tags: str

# --- 2. 基础清洗函数 ---
# 作用：把 "  请问   年假 " 变成 "请问 年假"，去除多余空格，保证向量计算更准。
def normalize_space(s: str) -> str:
    return " ".join(s.strip().split())

# --- 3. 生成标准 FAQ 库 (Knowledge Base) ---
def make_faqs(seed: int = 42) -> List[FAQ]:
    random.seed(seed)

    faqs: List[FAQ] = []

    # ---- 请假/考勤 ----
    leave_types = [
        ("年假", "年假可在系统中发起申请，建议提前提交，审批通过后生效。年假天数以公司政策与工龄规则为准。", "leave;attendance"),
        ("病假", "病假需在系统中提交请假单，并按要求补充病假证明。具体证明要求以公司制度为准。", "leave;attendance"),
        ("事假", "事假可在系统提交申请，说明事由与时间安排。审批通过后生效，是否带薪以公司制度为准。", "leave;attendance"),
        ("调休", "调休需满足可用调休额度，在系统中选择调休类型并提交审批。", "leave;attendance"),
        ("产假/陪产假", "产假/陪产假请按公司制度准备材料并在系统提交申请，HR 会协助确认时长与手续。", "leave;benefits"),
    ]
    for lt, ans, tags in leave_types:
        faqs.append(FAQ("", f"{lt}申请流程", f"{lt}怎么申请？需要走什么流程？", ans, tags))
        faqs.append(FAQ("", f"{lt}材料要求", f"申请{lt}需要提供哪些材料？", ans + "如有特殊情况请联系HR确认。", tags))

    attendance_qas = [
        ("迟到/早退怎么处理？", "如发生迟到/早退，请在系统按规定进行补卡/说明并提交审批。考勤结果以系统记录与审批为准。", "attendance"),
        ("忘记打卡怎么办？", "可在系统发起补卡申请，填写原因与时间，按流程审批后更新考勤记录。", "attendance"),
        ("加班怎么申请？", "加班需按部门要求在系统发起申请并保留相关记录，是否结算调休/加班费以制度为准。", "attendance;ot"),
        ("远程办公怎么申请？", "如需远程办公，请按部门与公司制度提前申请并获得审批，期间需保持工作可达与产出可追踪。", "attendance;remote"),
    ]
    for q, a, tags in attendance_qas:
        faqs.append(FAQ("", "考勤处理规则", q, a, tags))

    # ---- 薪酬/社保/福利 ----
    payroll_qas = [
        ("工资发放日是每月几号？", "工资发放日以公司财务安排为准，若遇节假日可能顺延或提前，具体以通知为准。", "payroll"),
        ("工资条在哪里查看？", "工资条可在指定平台/系统中查看，如无法访问请联系HR或IT支持。", "payroll"),
        ("个税申报相关问题找谁？", "个税申报一般由员工在个税APP完成，涉及公司信息或专项扣除证明可联系HR咨询。", "tax;payroll"),
        ("社保/公积金缴纳比例是多少？", "社保/公积金缴纳比例与基数以当地政策与公司制度为准，可联系HR获取最新口径。", "benefits"),
        ("补充医疗/商业保险怎么用？", "如公司提供补充医疗/商保，请按保险平台指引提交材料与报案，具体理赔以保险条款为准。", "benefits"),
    ]
    for q, a, tags in payroll_qas:
        faqs.append(FAQ("", "薪酬福利常见问题", q, a, tags))

    # ---- 入职/离职/转岗 ----
    lifecycle_qas = [
        ("入职需要准备哪些材料？", "入职前请按通知准备身份证明、学历证明、银行卡信息等材料；如需体检按公司安排执行。", "onboarding"),
        ("试用期多久？试用期考核怎么做？", "试用期时长与考核方式以劳动合同与公司制度为准，通常由直属主管与HR共同评估。", "onboarding"),
        ("离职流程怎么走？", "离职需在系统提交离职申请，完成审批、交接与资产归还；离职证明与结算按流程办理。", "offboarding"),
        ("转岗/调岗怎么申请？", "转岗/调岗通常需要直属主管与目标团队沟通确认，并按公司流程提交申请与审批。", "internal_move"),
    ]
    for q, a, tags in lifecycle_qas:
        faqs.append(FAQ("", "员工生命周期流程", q, a, tags))

    # ---- 报销/差旅 ----
    expense_types = [
        ("差旅", "差旅报销请按公司差旅制度，提交行程单、发票及相关凭证，按系统流程审批。", "expense;travel"),
        ("交通", "交通报销需提供合规票据与出行说明，按制度与系统流程提交审批。", "expense"),
        ("餐费", "餐费报销需按制度标准提供票据与事由说明，超标部分处理以制度为准。", "expense"),
        ("采购", "采购类报销需先走采购/审批流程，确保合规后再按财务要求报销。", "expense;procurement"),
    ]
    for et, ans, tags in expense_types:
        faqs.append(FAQ("", f"{et}报销流程", f"{et}如何报销？需要哪些凭证？", ans, tags))
        faqs.append(FAQ("", f"{et}报销时效", f"{et}报销需要在多久内提交？", "报销时效以公司财务制度为准，请尽量在规定时间内提交，避免影响结算。", tags))

    travel_qas = [
        ("出差如何申请？", "出差通常需要先提交出差申请，明确时间、地点、预算与目的，审批通过后再预订。", "travel"),
        ("机票/酒店怎么预订？", "如公司有指定平台请优先使用；若需自行预订，请保留合规票据与行程凭证。", "travel"),
    ]
    for q, a, tags in travel_qas:
        faqs.append(FAQ("", "差旅出行", q, a, tags))

    # ---- IT/权限/设备 ----
    it_qas = [
        ("邮箱/账号如何开通？", "账号通常在入职后由IT统一开通，如未开通请提交工单或联系IT支持。", "it;account"),
        ("忘记密码怎么办？", "可通过自助重置或提交工单处理，涉及权限变更需按流程审批。", "it;account"),
        ("VPN怎么申请？", "如需VPN，请按IT规定提交申请并完成审批，配置方式以IT指引为准。", "it"),
        ("办公软件许可证怎么申请？", "如需特定软件/许可证，请提交申请说明用途与期限，按部门与IT流程审批。", "it"),
        ("电脑/工牌等资产如何领用与归还？", "资产领用与归还需按公司资产流程登记，离职时需完成归还与核验。", "asset"),
    ]
    for q, a, tags in it_qas:
        faqs.append(FAQ("", "IT与资产支持", q, a, tags))

    # ---- 规章制度/假期 ----
    policy_qas = [
        ("法定节假日怎么安排？", "法定节假日一般按国家安排执行，如有调班或特殊安排以公司通知为准。", "holiday;policy"),
        ("年终奖/绩效奖金怎么发？", "绩效与奖金发放规则以公司制度与绩效结果为准，具体请关注公司公告或咨询HR。", "policy;payroll"),
        ("保密制度有哪些要求？", "请遵守公司保密与信息安全制度，禁止泄露敏感信息；如有疑问请咨询HR或安全负责人。", "policy;security"),
    ]
    for q, a, tags in policy_qas:
        faqs.append(FAQ("", "公司制度", q, a, tags))

    # ---- 扩充：通过“常见问法模板”自动增加一些变体（让条目数量更够）----
    expand_templates = [
        ("怎么", "如何"),
        ("怎么办", "如何处理"),
        ("需要哪些", "要准备什么"),
        ("在哪里", "在哪儿"),
    ]

    base = list(faqs)
    for item in base:
        q = item.question
        for a, b in expand_templates:
            if a in q and len(faqs) < 140:
                faqs.append(FAQ("", item.title, q.replace(a, b), item.answer, item.tags))

    # 分配 faq_id
    for idx, f in enumerate(faqs, start=1):
        f.faq_id = f"HR-{idx:03d}"

    return faqs

# --- 4. 生成测试集 Query (User Queries) ---
def make_queries(faqs: List[FAQ], per_faq: int = 2, seed: int = 42) -> List[Dict[str, str]]:
    random.seed(seed)
    variants_prefix = ["请问", "想问下", "咨询一下", "麻烦问下", ""]
    variants_suffix = ["", "？", "怎么弄？", "流程是什么？", "需要准备什么？"]

    rows = []
    for f in faqs:
        # 先放原 question（保证至少有一个强相关）
        rows.append({"query": normalize_space(f.question), "faq_id": f.faq_id})

        # 再生成若干变体
        for _ in range(per_faq):
            q = normalize_space(f.question)
            q2 = f"{random.choice(variants_prefix)}{q}{random.choice(variants_suffix)}"
            q2 = normalize_space(q2).replace("？？", "？")
            rows.append({"query": q2, "faq_id": f.faq_id})

    # 去重
    seen = set()
    dedup = []
    for r in rows:
        key = (r["query"], r["faq_id"])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup


def write_csv(path: str, header: List[str], rows: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per_faq_queries", type=int, default=2)
    args = ap.parse_args()

    faqs = make_faqs(seed=args.seed)
    faq_rows = [
        {
            "faq_id": f.faq_id,
            "title": f.title,
            "question": f.question,
            "answer": f.answer,
            "tags": f.tags,
        }
        for f in faqs
    ]
    queries = make_queries(faqs, per_faq=args.per_faq_queries, seed=args.seed)

    write_csv(
        os.path.join(args.out, "faq.csv"),
        ["faq_id", "title", "question", "answer", "tags"],
        faq_rows,
    )
    write_csv(
        os.path.join(args.out, "queries.csv"),
        ["query", "faq_id"],
        queries,
    )

    print(f"[OK] FAQ rows: {len(faq_rows)} -> {os.path.join(args.out, 'faq.csv')}")
    print(f"[OK] Query rows: {len(queries)} -> {os.path.join(args.out, 'queries.csv')}")


if __name__ == "__main__":
    main()
