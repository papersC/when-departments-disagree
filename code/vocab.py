"""Closed vocabularies and the organisational structure used by BRAIN.

Everything an agent may assert is drawn from these vocabularies. That closure
is what makes conflict detection mechanical and scoring deterministic.
"""

DEPARTMENTS = ["FIN", "LEG", "HR", "SEC", "OPS"]

DEPT_NAMES = {
    "FIN": "Finance",
    "LEG": "Legal and Compliance",
    "HR": "Human Resources",
    "SEC": "Information Security",
    "OPS": "Operations",
}

MODALITIES = ["must", "must_not", "should", "should_not", "may", "fact"]
DEONTIC = {"must", "must_not", "should", "should_not"}
BINDING = {"must", "must_not"}

# Modality pairs that cannot both hold of the same subject under jointly
# satisfiable conditions.
INCOMPATIBLE = {
    ("must", "must_not"), ("must_not", "must"),
    ("must", "should_not"), ("should_not", "must"),
    ("must_not", "should"), ("should", "must_not"),
    ("should", "should_not"), ("should_not", "should"),
}

# ---------------------------------------------------------------------------
# Claim types. owner is the single department whose deontic assertions bind.
# consulted departments may supply facts and advice but never obligations.
# ---------------------------------------------------------------------------
CLAIM_TYPES = {
    # Finance
    "payment_terms":            dict(owner="FIN", consulted=["LEG", "OPS"], mandatory=True),
    "budget_approval":          dict(owner="FIN", consulted=["OPS"],        mandatory=True),
    "expense_eligibility":      dict(owner="FIN", consulted=["HR"],         mandatory=False),
    "fx_handling":              dict(owner="FIN", consulted=["LEG"],        mandatory=False),
    "invoice_processing":       dict(owner="FIN", consulted=["OPS"],        mandatory=False),
    # Legal and compliance
    "contract_clause":          dict(owner="LEG", consulted=["FIN", "OPS"], mandatory=True),
    "liability_cap":            dict(owner="LEG", consulted=["FIN"],        mandatory=True),
    "data_processing_terms":    dict(owner="LEG", consulted=["SEC"],        mandatory=True),
    "dispute_forum":            dict(owner="LEG", consulted=[],             mandatory=False),
    "ip_assignment":            dict(owner="LEG", consulted=["HR"],         mandatory=False),
    "sanctions_screening":      dict(owner="LEG", consulted=["FIN"],        mandatory=True),
    # Human resources
    "employment_status":        dict(owner="HR",  consulted=["LEG", "FIN"], mandatory=True),
    "working_time":             dict(owner="HR",  consulted=["OPS"],        mandatory=False),
    "leave_entitlement":        dict(owner="HR",  consulted=[],             mandatory=False),
    "background_check":         dict(owner="HR",  consulted=["SEC", "LEG"], mandatory=True),
    "training_requirement":     dict(owner="HR",  consulted=["SEC"],        mandatory=False),
    # Information security
    "access_provisioning":      dict(owner="SEC", consulted=["OPS", "HR"],  mandatory=True),
    "data_classification":      dict(owner="SEC", consulted=["LEG"],        mandatory=True),
    "vendor_security_review":   dict(owner="SEC", consulted=["OPS", "LEG"], mandatory=True),
    "incident_reporting":       dict(owner="SEC", consulted=["LEG"],        mandatory=True),
    "device_control":           dict(owner="SEC", consulted=["OPS"],        mandatory=False),
    # Operations
    "vendor_onboarding":        dict(owner="OPS", consulted=["FIN", "SEC"], mandatory=True),
    "delivery_acceptance":      dict(owner="OPS", consulted=["FIN"],        mandatory=False),
    "service_continuity":       dict(owner="OPS", consulted=["SEC"],        mandatory=True),
    "change_window":            dict(owner="OPS", consulted=["SEC"],        mandatory=False),
}

TYPES = sorted(CLAIM_TYPES)
MANDATORY_TYPES = {t for t, v in CLAIM_TYPES.items() if v["mandatory"]}


def owner(t):
    return CLAIM_TYPES[t]["owner"]


def consulted(t):
    return list(CLAIM_TYPES[t]["consulted"])


def routed(t):
    return [owner(t)] + consulted(t)


# ---------------------------------------------------------------------------
# Subjects. Each subject belongs to one or more claim types. A subject shared
# by claim types with different owners is a potential cross owner conflict.
# ---------------------------------------------------------------------------
SUBJECTS = {
    # subject: list of claim types that may speak about it
    "grant_remote_access":        ["access_provisioning", "service_continuity"],
    "grant_admin_rights":         ["access_provisioning", "change_window"],
    "issue_shared_credential":    ["access_provisioning", "service_continuity"],
    "store_data_offshore":        ["data_classification", "data_processing_terms"],
    "encrypt_at_rest":            ["data_classification", "data_processing_terms"],
    "retain_records_seven_years": ["data_classification", "invoice_processing"],
    "share_data_with_vendor":     ["data_processing_terms", "vendor_security_review"],
    "run_penetration_test":       ["vendor_security_review", "change_window"],
    "accept_vendor_attestation":  ["vendor_security_review", "vendor_onboarding"],
    "report_incident_24h":        ["incident_reporting"],
    "notify_regulator":           ["incident_reporting", "sanctions_screening"],
    "allow_personal_device":      ["device_control", "working_time"],
    "prepay_invoice":             ["payment_terms", "invoice_processing"],
    "net_thirty_terms":           ["payment_terms"],
    "require_purchase_order":     ["payment_terms", "vendor_onboarding"],
    "obtain_two_approvals":       ["budget_approval", "vendor_onboarding"],
    "exceed_threshold_spend":     ["budget_approval"],
    "reimburse_travel":           ["expense_eligibility"],
    "hedge_exposure":             ["fx_handling"],
    "invoice_in_local_currency":  ["fx_handling", "payment_terms"],
    "cap_liability_at_fees":      ["liability_cap"],
    "accept_unlimited_indemnity": ["liability_cap", "contract_clause"],
    "include_audit_clause":       ["contract_clause", "vendor_security_review"],
    "include_termination_clause": ["contract_clause"],
    "select_local_forum":         ["dispute_forum"],
    "assign_ip_to_company":       ["ip_assignment"],
    "screen_counterparty":        ["sanctions_screening", "vendor_onboarding"],
    "classify_as_contractor":     ["employment_status"],
    "extend_probation":           ["employment_status", "background_check"],
    "schedule_night_shift":       ["working_time", "service_continuity"],
    "approve_carry_over_leave":   ["leave_entitlement"],
    "complete_reference_check":   ["background_check"],
    "complete_security_training": ["training_requirement", "access_provisioning"],
    "deploy_outside_window":      ["change_window", "service_continuity"],
    "accept_partial_delivery":    ["delivery_acceptance"],
    "maintain_hot_standby":       ["service_continuity"],
    "onboard_single_source":      ["vendor_onboarding"],
    "escalate_to_committee":      ["budget_approval", "vendor_onboarding"],
}

SUBJECT_LIST = sorted(SUBJECTS)

# Subjects on which two owners can collide, together with the registered
# precedence chain. A subject absent from this map has no registered
# precedence, so a cross owner contradiction on it must escalate.
PRECEDENCE = {
    "grant_remote_access":       ["SEC", "OPS"],
    "grant_admin_rights":        ["SEC", "OPS"],
    "store_data_offshore":       ["LEG", "SEC"],
    "share_data_with_vendor":    ["LEG", "SEC"],
    "require_purchase_order":    ["FIN", "OPS"],
    "accept_unlimited_indemnity": ["LEG", "FIN"],
    "include_audit_clause":      ["LEG", "SEC"],
    "prepay_invoice":            ["FIN", "OPS"],
    "complete_security_training": ["SEC", "HR"],
    "screen_counterparty":       ["LEG", "OPS"],
    # deliberately unregistered, so they escalate:
    #   issue_shared_credential, deploy_outside_window, schedule_night_shift,
    #   retain_records_seven_years, invoice_in_local_currency,
    #   accept_vendor_attestation, extend_probation, allow_personal_device
}

# ---------------------------------------------------------------------------
# Condition predicates. Terms marked as defined carry a departmental
# definition and are the site of definitional conflict.
# ---------------------------------------------------------------------------
PREDICATES = [
    "vendor_is_offshore", "contract_value_high", "data_is_personal",
    "engagement_is_short", "system_is_production", "counterparty_is_new",
    "service_is_critical", "worker_is_contractor", "access_is_privileged",
    "incident_is_material", "payment_is_recurring", "currency_is_foreign",
    "supplier_is_sole_source", "project_is_regulated", "change_is_emergency",
    "staff_is_remote", "asset_is_classified", "term_exceeds_year",
    "renewal_is_automatic", "volume_is_high",
]

# Terms whose meaning differs by department. The term map equates a subset.
DEFINED_TERMS = [
    "worker_is_contractor", "incident_is_material", "contract_value_high",
    "service_is_critical", "access_is_privileged", "data_is_personal",
]

# Registered term map: pairs of (department, department, term) treated as
# equivalent. Pairs absent from the map are definitional conflicts.
TERM_MAP = [
    ("HR", "LEG", "worker_is_contractor"),
    ("SEC", "LEG", "incident_is_material"),
    ("FIN", "LEG", "contract_value_high"),
    ("SEC", "LEG", "data_is_personal"),
    # deliberately unmapped: service_is_critical (OPS vs SEC),
    #                        access_is_privileged (SEC vs OPS),
    #                        worker_is_contractor (FIN vs HR)
]

POLICY_FAMILIES = {
    "FIN": ["FIN-PAY", "FIN-BUD", "FIN-EXP", "FIN-FX"],
    "LEG": ["LEG-CON", "LEG-LIA", "LEG-DPA", "LEG-SAN"],
    "HR": ["HR-EMP", "HR-TIM", "HR-BGC"],
    "SEC": ["SEC-ACC", "SEC-CLS", "SEC-VND", "SEC-INC"],
    "OPS": ["OPS-VND", "OPS-DEL", "OPS-CNT"],
}

FAMILY_TYPES = {
    "FIN-PAY": ["payment_terms", "invoice_processing"],
    "FIN-BUD": ["budget_approval"],
    "FIN-EXP": ["expense_eligibility"],
    "FIN-FX": ["fx_handling"],
    "LEG-CON": ["contract_clause", "dispute_forum", "ip_assignment"],
    "LEG-LIA": ["liability_cap"],
    "LEG-DPA": ["data_processing_terms"],
    "LEG-SAN": ["sanctions_screening"],
    "HR-EMP": ["employment_status", "leave_entitlement"],
    "HR-TIM": ["working_time", "training_requirement"],
    "HR-BGC": ["background_check"],
    "SEC-ACC": ["access_provisioning", "device_control"],
    "SEC-CLS": ["data_classification"],
    "SEC-VND": ["vendor_security_review"],
    "SEC-INC": ["incident_reporting"],
    "OPS-VND": ["vendor_onboarding"],
    "OPS-DEL": ["delivery_acceptance", "change_window"],
    "OPS-CNT": ["service_continuity"],
}

TYPE_FAMILY = {t: f for f, ts in FAMILY_TYPES.items() for t in ts}

# Revision cadence in quarters, deliberately different per department so that
# version skew arises from the schedule rather than from injection.
REVISION_CADENCE = {"FIN": 4, "LEG": 3, "HR": 6, "SEC": 2, "OPS": 5}

N_QUARTERS = 20  # five years

CONFLICT_CLASSES = ["C1", "C2", "C3", "C4", "C5", "C6"]
CONFLICT_NAMES = {
    "C1": "contradiction",
    "C2": "precedence",
    "C3": "jurisdiction",
    "C4": "staleness",
    "C5": "definitional",
    "C6": "omission",
}


# Deliberate ordering interactions between departments. Each entry names two
# rules owned by different departments whose ordering constraints point in
# opposite directions, which is the material from which precedence cycles (C2)
# arise. The constraint is emitted per version with probability ORDER_P, so a
# cycle exists in some quarters and not in others.
ORDER_CYCLES = [
    ("budget_approval", "obtain_two_approvals", "sanctions_screening", "screen_counterparty"),
    ("vendor_security_review", "run_penetration_test", "change_window", "deploy_outside_window"),
    ("training_requirement", "complete_security_training", "access_provisioning", "grant_remote_access"),
    ("contract_clause", "include_audit_clause", "vendor_security_review", "accept_vendor_attestation"),
    ("service_continuity", "maintain_hot_standby", "budget_approval", "exceed_threshold_spend"),
]
ORDER_P = 0.55
