"""Build outputs/operation_contract_details_v2.csv.

Evidence-only builder: every numeric threshold below was read in a source that
was actually fetched on 2026-09-15 (see sources/source_ledger.csv, S23-S33).
The script performs no network access and invents no value. Provenance tags are
carried per field so that DOCUMENTED and ASSUMED entries cannot be confused.

Schema = schema of outputs/operation_contract_details.csv plus:
  operation_phase, doc_locator_as_seen, measurement_height_reference,
  averaging_interval, threshold_basis_DOCUMENTED_or_ASSUMED, sensitivity_range,
  reviewer_attack_risk, mitigation, date_checked
(source_id, page_or_section, evidence_grade and open_issue are retained unchanged.)
"""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = PROJECT_ROOT / "outputs" / "operation_contract_details_v2.csv"

COLUMNS = [
    "contract_id",
    "source_id",
    "page_or_section",
    "doc_locator_as_seen",
    "equipment_scope",
    "work_stage",
    "operation_phase",
    "variable_name",
    "measurement_height",
    "temporal_support",
    "averaging_interval",
    "start_limit",
    "continuation_limit",
    "unit",
    "threshold_basis_DOCUMENTED_or_ASSUMED",
    "evidence_class",
    "required_duration",
    "duration_source",
    "safe_terminal_state",
    "interruption_permitted",
    "failure_response",
    "recovery_duration_source",
    "resource_hold_during_pause",
    "transfer_scope",
    "sensitivity_range",
    "reviewer_attack_risk",
    "mitigation",
    "evidence_grade",
    "measurement_height_reference",
    "open_issue",
    "date_checked",
]

MFR = "manufacturer operation and service manual"
CITED_FIELD = "cited in field"

ROWS: list[dict[str, str]] = []


def add(**kw: str) -> None:
    row = {c: "" for c in COLUMNS}
    row.update(kw)
    missing = [c for c in COLUMNS if row[c] == "" and c != "evidence_class"]
    if missing:
        raise ValueError(f"row {kw.get('contract_id')}/{kw.get('variable_name')} missing {missing}")
    ROWS.append(row)


# Row-level evidence class. These four categories must never be blurred.
#   DOCUMENTED_LIMIT                 numeric threshold read verbatim in a source
#   DOCUMENTED_LIMIT_OUR_ARITHMETIC  numeric threshold derived by arithmetic on two
#                                    or more documented values (derivation shown below)
#   DOCUMENTED_PROCEDURE             documented requirement that contains no number
#   NOT_OBTAINABLE                   source states the rule but publishes no number
EVIDENCE_CLASS = {
    ("OP01_tower_crane_segment_lift", "wind speed at crane anemometer"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift", "wind speed for precision slewing and clamp release"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift", "industry-recommended in-service wind speed limit for tower cranes"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift", "out-of-service (storm) wind speed"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift", "numeric wind limit (regulatory basis)"): "DOCUMENTED_PROCEDURE",
    ("OP01_tower_crane_segment_lift", "numeric wind limit (US regulatory basis)"): "DOCUMENTED_PROCEDURE",
    ("OP01_tower_crane_segment_lift_CN", "wind speed at the highest point of the machine (安装拆卸)"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift_CN", "code-level wind speed limit for open-air lifting and for installation/dismantling"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift_CN", "wind speed limit for concrete placing with a boom"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift_CN", "tower-crane wind speed limit at maximum height"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift_CN", "what the code's wind alarm actually measures"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift_CN", "Beaufort-force-based stop rule for work at height"): "DOCUMENTED_LIMIT",
    ("OP01_tower_crane_segment_lift", "securing procedure (storm state)"): "DOCUMENTED_PROCEDURE",
    ("OP02_segmental_epoxy_jointing", "substrate (concrete mating-surface) temperature"): "DOCUMENTED_LIMIT",
    ("OP02_segmental_epoxy_jointing", "substrate temperature upper bound / heated-enclosure cap"): "DOCUMENTED_LIMIT",
    ("OP02_segmental_epoxy_jointing", "elapsed time from epoxy mixing to applied contact pressure"): "DOCUMENTED_LIMIT_OUR_ARITHMETIC",
    ("OP02_segmental_epoxy_jointing", "post-join substrate temperature hold"): "DOCUMENTED_LIMIT",
    ("OP03_concrete_placement_delivery", "concrete mixture temperature at placing (入模温度)"): "DOCUMENTED_LIMIT",
    ("OP03_concrete_placement_delivery", "outdoor daily mean air temperature (winter and hot-weather triggers)"): "DOCUMENTED_LIMIT",
    ("OP03_concrete_placement_delivery", "concrete mixture discharge temperature (出机温度)"): "DOCUMENTED_LIMIT",
    ("OP03_concrete_placement_delivery", "rainfall intensity category"): "NOT_OBTAINABLE",
    ("OP03_concrete_placement_delivery", "surface-to-ambient temperature difference and layer temperature"): "DOCUMENTED_LIMIT",
    ("HS2_segment_installation_BASELINE_ONLY", "gust wind speed"): "NOT_OBTAINABLE",
}


def tag_evidence_class() -> None:
    for row in ROWS:
        key = (row["contract_id"], row["variable_name"])
        if key not in EVIDENCE_CLASS:
            raise KeyError(f"no evidence_class registered for {key}")
        row["evidence_class"] = EVIDENCE_CLASS[key]



# ---------------------------------------------------------------------------
# OP01 -- tower-crane lifting of a precast deck segment
# ---------------------------------------------------------------------------
add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S23",
    page_or_section="Ch. 2.1 item 4; Ch. 3.4; Sec. 3.4.1(h); Sec. 10.7.3.2",
    doc_locator_as_seen=(
        "Yongmao STT293 Tower Crane Operation & Service Manual, en-version 2.0, "
        "Ch. 2.1 item 4) 'the max. wind speed for operating is 20m/s'; Ch. 3.4 "
        "'the max. working wind speed is 20m/s'; Sec. 3.4.1(h) 'If the wind speed "
        "exceeds 20 m/s, it can sent audible and visual alarm, then the tower crane "
        "must stop working'; Sec. 10.7.3.2 'Set the limit value to 20 when it working'"
    ),
    equipment_scope="Yongmao STT293 tower crane (hammerhead, A4 duty), manufacturer-rated",
    work_stage="in-service lifting of a precast concrete deck segment",
    operation_phase="MAIN_LIFT",
    variable_name="wind speed at crane anemometer",
    measurement_height=(
        "crane-mounted anemoscope; manual does NOT state the sensor height. Sec. 3.4.1(h) "
        "requires an anemoscope when working height > 50 m. Height treated as NOT_ESTABLISHED."
    ),
    measurement_height_reference=(
        "crane-mounted anemoscope; the manufacturer manual does NOT state the sensor height above "
        "ground. Contrast the Chinese codes (S35, S37), which do state a height."
    ),
    temporal_support="instantaneous anemometer reading at decision time",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="20",
    continuation_limit="20",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "NOT_ESTABLISHED: manufacturer manual sets no time window; it is a magnitude stop rule only"
    ),
    duration_source="no published duration found for one segmental lift cycle (open item)",
    safe_terminal_state=(
        "load landed and released, hook raised, trolley driven to jib foot, slewing brake "
        "released to weathervane (Sec. 3.4.3 a-c). Out-of-service state is a separate variable."
    ),
    interruption_permitted="yes during the lift; load must be set down before securing",
    failure_response=(
        "at 20 m/s audible+visual alarm and the crane must stop working (Sec. 3.4.1(h), "
        "Sec. 3.4.2 special notice). No instruction is given for a load already in the air."
    ),
    recovery_duration_source="no recovery time is documented by the manufacturer (open item)",
    resource_hold_during_pause=(
        "ASSUMED: crane, crew and the suspended-load exclusion zone are held while the "
        "segment is set down"
    ),
    transfer_scope="single crane, single segment; not transferable to other crane models",
    sensitivity_range=(
        "sweep 16.5 to 20 m/s (16.5 = UK industry recommendation, S24); "
        "sweep 0.70x-1.30x on whatever value is used"
    ),
    reviewer_attack_risk=(
        "HIGH: 20 m/s is one model's manual figure; the manual never states the averaging "
        "interval or sensor height, so a reviewer can say the project compares a forecast "
        "gust to an unstated reference quantity"
    ),
    mitigation=(
        "label 20 m/s as manufacturer in-service limit at crane anemometer; carry averaging "
        "interval as an explicit swept parameter; report the UK 16.5 m/s industry figure as "
        "the conservative alternative; never call 20 m/s a code requirement"
    ),
    evidence_grade="PRIMARY_MANUFACTURER_MANUAL_TEXT_SEEN",
    open_issue="averaging interval, sensor height and single-lift duration all NOT_ESTABLISHED",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S23",
    page_or_section="Sec. 2.4 item 1(c); Sec. 3.4.1(c) mechanical description; Sec. 10.7.3.2; Sec. 10.7.4.1",
    doc_locator_as_seen=(
        "Yongmao STT293 manual, Sec. 2.4 '1) Every time before starting up: ... c) Remove the "
        "cushion block, release the rail clamping device and other fixing devices (wind speed "
        "<=13m/s)'; Sec. 10.7.3.2 'Set the limit value to 13 when it hoisting'; Sec. 10.7.4.1 "
        "'W1 - 13m/s limit alarm set'"
    ),
    equipment_scope="same crane; slewing-brake / rail-clamp release function",
    work_stage="low-speed positioning and precision placement of the segment",
    operation_phase="POSITION_AND_RELEASE_CLAMPS",
    variable_name="wind speed for precision slewing and clamp release",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="crane-mounted anemoscope (height NOT_ESTABLISHED)",
    temporal_support="instantaneous anemometer reading",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="13",
    continuation_limit="13",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated; it is a magnitude gate on a specific crane function",
    duration_source="manufacturer manual sets no duration for the positioning step",
    safe_terminal_state=(
        "segment landed and held by the slewing brake only while wind <= 13 m/s; above that "
        "the jib must be free to weathervane"
    ),
    interruption_permitted="yes; below 13 m/s the brake must not be applied to hold the jib",
    failure_response=(
        "release the slewing brake and let the jib weathervane; do not use the brake above 13 m/s"
    ),
    recovery_duration_source="none documented",
    resource_hold_during_pause="ASSUMED: same crew and crane held",
    transfer_scope="crane-function-specific; not a general lifting limit",
    sensitivity_range="sweep 11 to 16 m/s",
    reviewer_attack_risk=(
        "MEDIUM: a reviewer may read 13 m/s as the governing lift limit and claim the project "
        "contradicts itself when it also cites 20 m/s"
    ),
    mitigation=(
        "state explicitly that 13 m/s gates a crane FUNCTION (slewing-brake use, clamp release) "
        "while 20 m/s gates in-service OPERATION; encode both as separate variables"
    ),
    evidence_grade="PRIMARY_MANUFACTURER_MANUAL_TEXT_SEEN",
    open_issue="this 13 m/s function limit is not an operational stop-work threshold per se",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S24",
    page_or_section="CPA TIN 101, 'The Effect of Wind on Mobile Cranes In-service', p.1",
    doc_locator_as_seen=(
        "Construction Plant-hire Association, Crane Interest Group, Mobile Crane Technical "
        "Information Note TIN 101 Issue A (04.12.09), p.1: 'following a review of in-service "
        "wind speeds by the CPA Tower Crane Interest Group, involving tower crane suppliers, "
        "major contractors and the Health and Safety Executive; the industry recommended maximum "
        "wind speed at which tower cranes operating in the UK must be taken out of service is "
        "38 mph (16.5 m/s, 60 kph)'"
    ),
    equipment_scope="tower cranes operating in the UK (industry recommendation)",
    work_stage="in-service lifting",
    operation_phase="MAIN_LIFT",
    variable_name="industry-recommended in-service wind speed limit for tower cranes",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "TIN 101 warns that 'most weather forecast wind speeds are for a height of 10m above "
        "ground and should be corrected for greater heights'"
    ),
    temporal_support="industry recommendation; no averaging interval stated in TIN 101",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="16.5",
    continuation_limit="16.5",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED=(
        "DOCUMENTED (industry recommendation, not a standard clause and not law)"
    ),
    required_duration="not applicable; single magnitude threshold",
    duration_source="not applicable",
    safe_terminal_state="crane taken out of service per the manufacturer's instruction manual",
    interruption_permitted="yes",
    failure_response="take the crane out of service; the operator may stop earlier and cannot be overridden",
    recovery_duration_source="not documented",
    resource_hold_during_pause="ASSUMED: resources held",
    transfer_scope=(
        "UK tower-crane practice; also states the mobile-crane duty-chart maximum is normally "
        "31 mph (14 m/s) and 'frequently well below'"
    ),
    sensitivity_range="sweep 14 to 20 m/s; this row is the conservative end-member",
    reviewer_attack_risk=(
        "MEDIUM: TIN 101 is a plant-hire trade body note, not a code; a reviewer can ask why a "
        "UK trade note governs a non-UK site"
    ),
    mitigation=(
        "present it as a corroborating industry recommendation, not as the legal basis, and run "
        "the main experiment at both 16.5 and 20 m/s so the choice is swept rather than asserted"
    ),
    evidence_grade="PRIMARY_TRADE_BODY_NOTE_TEXT_SEEN",
    open_issue="no averaging interval; recommendation applies to tower cranes operated in the UK",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S23",
    page_or_section="Ch. 2.1 item 4; Sec. 3.4.3; Sec. 10.7 note",
    doc_locator_as_seen=(
        "Yongmao STT293 manual Ch. 2.1 item 4) 'the max. wind speed out of service is 50m/s'; "
        "Sec. 3.4.3 'Lift the hook to the top end; Drive the trolley to the jib foot, start the "
        "weather-vane and brake device, to make the jib slewing freely (weather-vane effect)'. "
        "Second jurisdiction for the securing state: S25 DGUV Vorschrift 52 Sec. 30(6)2. A THIRD, "
        "independent Chinese source (S38 GB 5144-2006 Sec. 6.3.4/6.8) likewise requires free slewing "
        "plus rail clamping in the non-working state and states NO number."
    ),
    equipment_scope="same crane, out-of-service / storm condition",
    work_stage="parked crane between shifts and during storms",
    operation_phase="OUT_OF_SERVICE",
    variable_name="out-of-service (storm) wind speed",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="not stated in the manual (NOT_ESTABLISHED)",
    temporal_support="design out-of-service state; not an hourly decision variable",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="50",
    continuation_limit="50",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable; a design state, not a work window",
    duration_source="not applicable",
    safe_terminal_state=(
        "hook at top, trolley at jib foot, weathervane effect engaged so the jib slews freely, "
        "power off, rain measures applied, travelling cranes anchored on 4 rail clamps"
    ),
    interruption_permitted="not applicable; this is the terminal state",
    failure_response=(
        "DGUV 52 Sec. 30(6)1 requires securing 'rechtzeitig spaetestens bei Erreichen der fuer den "
        "Kran kritischen Windgeschwindigkeit und bei Arbeitsschluss' (in good time, at the latest "
        "on reaching the crane-critical wind speed and at the end of work)"
    ),
    recovery_duration_source="not documented; return to service is not timed in any source seen",
    resource_hold_during_pause="crane is released from the work face; no crew hold documented",
    transfer_scope="design state only; must NOT be used as a work-continuation limit",
    sensitivity_range="no sensitivity: treated as a hard design state, not swept",
    reviewer_attack_risk=(
        "LOW for the value, HIGH for misuse: a 50 m/s out-of-service figure looks generous next "
        "to a 20 m/s in-service figure and invites the project to over-claim usable weather"
    ),
    mitigation=(
        "keep OUT_OF_SERVICE strictly separate from the work-window logic and assert in code that "
        "the 50 m/s state can never authorise a start"
    ),
    evidence_grade="PRIMARY_MANUFACTURER_MANUAL_TEXT_SEEN",
    open_issue="averaging interval and sensor height not stated by the manufacturer",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S25",
    page_or_section="DGUV Vorschrift 52 'Krane', Sec. 30(6)1 and Durchfuehrungsanweisung to Sec. 30(6)1",
    doc_locator_as_seen=(
        "DGUV Vorschrift 52, Sec. 30(6)1: 'dem Wind ausgesetzte Krane nicht ueber die vom "
        "Kranhersteller festgelegten Grenzen hinaus betrieben werden sowie rechtzeitig "
        "spaetestens bei Erreichen der fuer den Kran kritischen Windgeschwindigkeit und bei "
        "Arbeitsschluss durch die Windsicherung festgelegt werden'. DA zu Sec. 30 Abs. 6 Nr. 1: "
        "'Grenzen fuer den Einsatz eines Kranes bei Windeinwirkung gibt der Kranhersteller in der "
        "Betriebsanleitung - gegebenenfalls auch in der Tragfaehigkeits-tabelle - an.'"
    ),
    equipment_scope="all cranes within the German DGUV accident-prevention regulation",
    work_stage="in-service operation and end-of-shift securing",
    operation_phase="GOVERNING_RULE",
    variable_name="numeric wind limit (regulatory basis)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="not specified by the regulation",
    temporal_support="continuous duty to secure the crane",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="NO_NUMERIC_VALUE_IN_REGULATION",
    continuation_limit="NO_NUMERIC_VALUE_IN_REGULATION",
    unit="n/a",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable",
    duration_source="not applicable",
    safe_terminal_state="crane secured by the manufacturer's wind-securing arrangement",
    interruption_permitted="yes",
    failure_response="stop exceeding the manufacturer limit and secure the crane",
    recovery_duration_source="not documented",
    resource_hold_during_pause="not addressed by the regulation",
    transfer_scope=(
        "KEY EVIDENCE: a national crane safety regulation defers the numeric wind limit to the "
        "crane manufacturer rather than fixing one"
    ),
    sensitivity_range="not applicable",
    reviewer_attack_risk=(
        "LOW: this row is negative evidence and actually protects the contract, because it shows "
        "why no single code number exists"
    ),
    mitigation=(
        "cite this row whenever a reviewer asks why the contract does not use one universal wind "
        "number; it documents the delegation to the manufacturer"
    ),
    evidence_grade="PRIMARY_REGULATION_TEXT_SEEN",
    open_issue="none for the delegation rule; no number is available from this source by design",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S25",
    page_or_section="DGUV Vorschrift 52, Sec. 30(6)2",
    doc_locator_as_seen=(
        "DGUV Vorschrift 52, Sec. 30(6)2, on tower slewing cranes and jib cranes that must swing "
        "into the wind for stability: before leaving the control station the operator must unload "
        "the hook and lifting gear, raise the hook, release the slewing brake, bring the trolley to "
        "the rest position and the jib to its widest position"
    ),
    equipment_scope="tower slewing cranes and jib cranes",
    work_stage="end of shift; high-wind securing",
    operation_phase="OUT_OF_SERVICE",
    variable_name="securing procedure (storm state)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="not applicable",
    temporal_support="at end of shift and when the critical wind speed is reached",
    averaging_interval="not applicable",
    start_limit="not applicable",
    continuation_limit="not applicable",
    unit="n/a",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable",
    duration_source="not applicable",
    safe_terminal_state=(
        "load and lifting gear unhooked, hook raised, slewing brake released, trolley at rest "
        "position, jib in its widest position so it can swing into the wind"
    ),
    interruption_permitted="not applicable",
    failure_response=(
        "if the jib may be driven against obstacles the operator must carry out the measures "
        "fixed by the employer"
    ),
    recovery_duration_source="not documented",
    resource_hold_during_pause="not addressed",
    transfer_scope=(
        "a citable, jurisdiction-level definition of the secured terminal state; corroborates the "
        "manufacturer's weathervane procedure in S23"
    ),
    sensitivity_range="not applicable",
    reviewer_attack_risk=(
        "LOW: it is a procedure, not a threshold; the risk is only that a reader mistakes it for "
        "a numeric limit"
    ),
    mitigation="tag this row PROCEDURE in the JSON contract and never read a number out of it",
    evidence_grade="PRIMARY_REGULATION_TEXT_SEEN",
    open_issue="none",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift",
    source_id="S26",
    page_or_section="29 CFR 1926.1417(n); 29 CFR 1926.1435(b)(4)(iii); 29 CFR 1926.1435(e)(6)(v)",
    doc_locator_as_seen=(
        "29 CFR 1926.1417(n): 'The competent person must adjust the equipment and/or operations to "
        "address the effect of wind, ice, and snow on equipment stability and rated capacity.' "
        "29 CFR 1926.1435(b)(4)(iii) 'Wind speed. Wind must not exceed the speed recommended by the "
        "manufacturer or, where manufacturer does not specify this information, the speed determined "
        "by a qualified person.' 29 CFR 1926.1435(e)(6)(v): a wind speed indicator must display wind "
        "speed and be mounted above the upper rotating structure on tower cranes."
    ),
    equipment_scope="cranes and derricks in construction (US federal regulation)",
    work_stage="operation and tower-crane erection/climbing/dismantling",
    operation_phase="GOVERNING_RULE",
    variable_name="numeric wind limit (US regulatory basis)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "wind speed indicator above the upper rotating structure (tower cranes); "
        "no height above ground is prescribed"
    ),
    temporal_support="competent-person judgement, continuous",
    averaging_interval="NOT_ESTABLISHED_IN_SOURCE",
    start_limit="NO_NUMERIC_VALUE_IN_REGULATION",
    continuation_limit="NO_NUMERIC_VALUE_IN_REGULATION",
    unit="n/a",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable",
    duration_source="not applicable",
    safe_terminal_state=(
        "1926.1417(h): on a local storm warning the competent person determines whether to "
        "implement manufacturer recommendations for securing the equipment"
    ),
    interruption_permitted="yes; the competent person must adjust or stop operations",
    failure_response="adjust equipment and/or operations, or stop, when wind threatens stability or capacity",
    recovery_duration_source="not documented",
    resource_hold_during_pause="not addressed by the regulation",
    transfer_scope=(
        "SECOND independent jurisdiction confirming that the numeric limit is delegated to the "
        "manufacturer; also the only source seen that mandates the instrument location"
    ),
    sensitivity_range="not applicable",
    reviewer_attack_risk=(
        "LOW as evidence, but a reviewer may ask for the OSHA numeric limit and be dissatisfied "
        "that none exists"
    ),
    mitigation=(
        "state plainly that OSHA Subpart CC contains no numeric wind threshold and requires "
        "manufacturer or qualified-person values; use the S23 manual value as the concrete number"
    ),
    evidence_grade="PRIMARY_REGULATION_TEXT_SEEN",
    open_issue="no federal numeric threshold exists to cite",
    date_checked="2026-09-15",
)

# ---------------------------------------------------------------------------
# OP02 -- concrete segmental match-cast epoxy jointing
# ---------------------------------------------------------------------------
add(
    contract_id="OP02_segmental_epoxy_jointing",
    source_id="S27",
    page_or_section="VDOT IIM-S&B-91 (13 Dec 2016), Sec. 453-5.3; Sec. 453-5.7.1",
    doc_locator_as_seen=(
        "VDOT IIM-S&B-91, Sec. 453-5.3 Substrate Temperatures and Epoxy Formulation: 'Apply the "
        "epoxy bonding agent only when the substrate temperature of both surfaces to be joined is "
        "between 40 degrees F and 115 degrees F.' Sec. 453-4.4 restates the range for formulation "
        "selection. Sec. 453-5.7.1 Cooling in Hot Weather: 'If the substrate temperature exceeds "
        "115 degrees F, do not proceed with epoxy jointing.'"
    ),
    equipment_scope=(
        "match-cast precast concrete segmental bridge joints; ASTM C881 Type VI/VII Grade 3 epoxy"
    ),
    work_stage="jointing of a newly erected segment to the previously placed segment",
    operation_phase="SUBSTRATE_TEMPERATURE_GATE",
    variable_name="substrate (concrete mating-surface) temperature",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "measured on the concrete mating surfaces of the joint (substrate temperature), "
        "not air temperature"
    ),
    temporal_support="at the moment of epoxy application and through the open time",
    averaging_interval="instantaneous surface temperature; no averaging period is specified",
    start_limit="40",
    continuation_limit="40",
    unit="degrees F",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "the temperature must hold through application and the contact-pressure window "
        "(see OP02_open_time rows)"
    ),
    duration_source="Sec. 453-5.1, 453-5.4 and 453-5.6 define the window contents, not its length",
    safe_terminal_state=(
        "joint filled, discernible extruded epoxy bead along the exposed joint edges, "
        "contact pressure maintained until the epoxy has hardened and cured"
    ),
    interruption_permitted=(
        "NO interruption is permitted inside the open-time window; the joint must be completed or "
        "the segments separated and cleaned"
    ),
    failure_response=(
        "below 40 degrees F: either stop, or use an artificial enclosure and raise the whole joint "
        "surface to at least 40 degrees F (Sec. 453-5.7.2)"
    ),
    recovery_duration_source=(
        "Sec. 453-5.7.2 item 4: maintain substrate between 40 and 95 degrees F for at least "
        "24 hours after joining the surfaces"
    ),
    resource_hold_during_pause=(
        "DOCUMENTED: the joint position, the erection equipment contact pressure and the crew are "
        "held for the curing period; contact pressure must not be reduced until the epoxy has cured"
    ),
    transfer_scope=(
        "a US state DOT instructional memorandum that incorporates FDOT Specification 452/453; "
        "not a European or ISO standard"
    ),
    sensitivity_range="sweep the lower bound 35 to 45 degrees F in 2.5 degree steps",
    reviewer_attack_risk=(
        "MEDIUM: a state DOT IIM is a contractual specification for one owner, not a national code"
    ),
    mitigation=(
        "label the locator precisely as VDOT IIM-S&B-91 Sec. 453-5.3 and state that it is a "
        "specification-level requirement; note that GB 50666-2011 Sec. 8.1.2 gives an independent "
        "5 degrees C (=41 degrees F) lower bound for a different material placement operation"
    ),
    evidence_grade="PRIMARY_OWNER_SPECIFICATION_TEXT_SEEN",
    open_issue="the 40/115 degrees F window is an owner specification and site-specific by nature",
    date_checked="2026-09-15",
)

add(
    contract_id="OP02_segmental_epoxy_jointing",
    source_id="S27",
    page_or_section="VDOT IIM-S&B-91, Sec. 453-5.3; Sec. 453-5.7.1; Sec. 453-5.7.2 items 3-4",
    doc_locator_as_seen=(
        "Sec. 453-5.3 upper bound 115 degrees F; Sec. 453-5.7.1 'If the substrate temperature "
        "exceeds 115 degrees F, do not proceed with epoxy jointing.' Sec. 453-5.7.2 item 3: "
        "'Prevent localized heating and the temperature of the substrate exceeding 95 degrees F at "
        "any point on the surface. Direct flame heating of the concrete is not allowed.' "
        "Sec. 453-5.7.2 closing sentence: 'Epoxy jointing operations may proceed if the air "
        "temperature is above 45 degrees F and rising and the limitations above are met.'"
    ),
    equipment_scope="same joint operation, hot-weather and artificially heated cases",
    work_stage="jointing",
    operation_phase="SUBSTRATE_TEMPERATURE_UPPER_BOUND",
    variable_name="substrate temperature upper bound / heated-enclosure cap",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="concrete mating surfaces; air temperature for the 45 degrees F rule",
    temporal_support="at the moment of application",
    averaging_interval="instantaneous; no averaging period specified",
    start_limit="115",
    continuation_limit="115",
    unit="degrees F",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable; a magnitude stop rule",
    duration_source="not applicable",
    safe_terminal_state="segments separated and faces protected if the upper bound is breached",
    interruption_permitted="yes before mixing; no once epoxy has been applied to both faces",
    failure_response=(
        "above 115 degrees F do not proceed; cooling by shading and/or wetting is allowed but the "
        "'no free moisture at the time of application' rule must still hold (Sec. 453-5.2, 453-5.7.1)"
    ),
    recovery_duration_source=(
        "not stated for the hot-weather case; the 24-hour hold in Sec. 453-5.7.2 applies only to "
        "the artificially heated cold-weather case"
    ),
    resource_hold_during_pause="resources wait for a cooler period; no fixed duration is documented",
    transfer_scope="specification-level; the 95 degrees F cap applies only inside a heated enclosure",
    sensitivity_range=(
        "sweep 95 to 115 degrees F for the hot-weather stop; sweep the 45 degrees F air-temperature "
        "rule 40 to 50 degrees F"
    ),
    reviewer_attack_risk=(
        "LOW-MEDIUM: three different temperatures (45 air, 95 cap in enclosure, 115 substrate stop) "
        "can be conflated by a careless reader"
    ),
    mitigation=(
        "expose the three temperatures as three separate JSON fields with distinct applicability "
        "flags (air / enclosure-interior / substrate)"
    ),
    evidence_grade="PRIMARY_OWNER_SPECIFICATION_TEXT_SEEN",
    open_issue="hot-weather recovery duration is not documented",
    date_checked="2026-09-15",
)

add(
    contract_id="OP02_segmental_epoxy_jointing",
    source_id="S27",
    page_or_section="VDOT IIM-S&B-91, Sec. 453-5.1; Sec. 453-5.6; Sec. 453-4.5.2; Sec. 453-5.4",
    doc_locator_as_seen=(
        "Sec. 453-5.1: the erection manual must ensure 'the time elapsing between mixing components "
        "of the first batch of epoxy bonding agent applied to the joining surfaces of precast concrete "
        "segments and the application of a compressive contact pressure across the joint does not "
        "exceed 70% of the open time for the particular formulation of epoxy bonding agent used.' "
        "Sec. 453-4.5.2: 'The contact time (open time) of the mixed epoxy-bonding agent shall be: "
        "Normal-Set Epoxy 60 minutes, minimum; Slow-Set Epoxy 6 hours, minimum.' Sec. 453-5.6: 'If "
        "the time between combining the components of the epoxy bonding agent and applying the "
        "compressive contact pressure exceeds 70% of the minimum open time, immediately separate the "
        "segments and clean in accordance with 453-5.8.' Sec. 453-5.4: 'Schedule mixing of the epoxy "
        "bonding agent so that the material in a batch is applied to the face of a joint within a "
        "maximum of 20 minutes after combining the components.'"
    ),
    equipment_scope="mixed epoxy bonding agent, normal-set and slow-set formulations",
    work_stage="joint making: mix, apply, bring together, apply contact pressure",
    operation_phase="OPEN_TIME_WINDOW",
    variable_name="elapsed time from epoxy mixing to applied contact pressure",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="not applicable (time variable)",
    temporal_support=(
        "elapsed-time stopwatch from combining components; the manufacturer/VDOT window is a "
        "non-preemptive interval"
    ),
    averaging_interval="not applicable",
    start_limit="0",
    continuation_limit="42",
    unit="minutes (normal-set formulation)",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "normal-set epoxy open time minimum 60 minutes; the maximum usable elapsed time is "
        "70% x 60 = 42 minutes before the contact pressure must already be applied"
    ),
    duration_source=(
        "Sec. 453-4.5.2 gives the 60-minute minimum open time; Sec. 453-5.1/453-5.6 give the 70% rule. "
        "The 42-minute figure is our arithmetic on two documented values, not a printed number."
    ),
    safe_terminal_state=(
        "contact pressure applied and maintained, bead of epoxy extruded all around the joint, "
        "internal ducts swabbed"
    ),
    interruption_permitted=(
        "NO. Reducing or interrupting contact pressure before cure is not permitted, and exceeding "
        "70% of the open time forces separation of the segments."
    ),
    failure_response=(
        "exceed the 70% limit, or leave the joint incompletely filled and sealed: separate the "
        "segments and remove all epoxy from the faces with spatulas and approved solvent"
    ),
    recovery_duration_source=(
        "Sec. 453-5.8: 'Do not re-apply epoxy until the faces have been properly cleaned and "
        "solvents dispersed, for a period of 24 hours.' This is a documented 24-hour recovery."
    ),
    resource_hold_during_pause=(
        "DOCUMENTED: the segment, the erection equipment, the contact-pressure system and the crew "
        "are held from mixing until the epoxy has hardened"
    ),
    transfer_scope=(
        "the only operation in this contract with a fully documented non-preemptive window AND a "
        "documented recovery duration"
    ),
    sensitivity_range=(
        "sweep the usable window 30 / 42 / 60 minutes; sweep the recovery duration 0 / 12 / 24 hours "
        "(24 h is documented, 0 and 12 h are NOT documented and exist only as a stress test)"
    ),
    reviewer_attack_risk=(
        "LOWEST of all operations, but a reviewer can still object that 42 minutes is our arithmetic "
        "and that a specific project's erection manual fixes a different value"
    ),
    mitigation=(
        "print both documented numbers (60-minute minimum open time, 70% rule) next to the derived "
        "42 minutes and label the derived value as our calculation; expose the window as a swept "
        "parameter"
    ),
    evidence_grade="PRIMARY_OWNER_SPECIFICATION_TEXT_SEEN",
    open_issue="the actual project erection manual is not public, so 42 minutes is a specification default",
    date_checked="2026-09-15",
)

add(
    contract_id="OP02_segmental_epoxy_jointing",
    source_id="S27",
    page_or_section="VDOT IIM-S&B-91, Sec. 453-5.7.2 items 2-4 and closing sentence; Sec. 453-5.2",
    doc_locator_as_seen=(
        "Sec. 453-5.7.2 'Artificial Heating in Cold Weather': 'If electing to erect segments in cold "
        "weather when the substrate temperature of the mating concrete surfaces is below 40 degrees F, "
        "an artificial environment may be used ... 2. Raise the temperature of the concrete substrate "
        "across the entire joint surface to at least 40 degrees F. 3. ... not exceeding 95 degrees F at "
        "any point ... 4. Maintain the temperature of the substrate surfaces between 40 degrees F and "
        "95 degrees F for at least 24 hours after joining the surfaces.' Closing: 'Epoxy jointing "
        "operations may proceed if the air temperature is above 45 degrees F and rising and the "
        "limitations above are met.' Sec. 453-5.2 requires the surfaces to be free of free moisture: "
        "'Free moisture will be considered present if a dry rag, after being wiped over the surface, "
        "becomes damp.'"
    ),
    equipment_scope="joint in an artificial heated enclosure, cold weather",
    work_stage="jointing and post-join cure hold",
    operation_phase="POST_JOIN_CURE_HOLD",
    variable_name="post-join substrate temperature hold",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="concrete mating surfaces inside the enclosure",
    temporal_support="24-hour continuous hold after joining",
    averaging_interval="continuous hold; no averaging window specified",
    start_limit="40",
    continuation_limit="95",
    unit="degrees F",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "at least 24 hours after joining the surfaces, with substrate between 40 and 95 degrees F, "
        "and air temperature above 45 degrees F and rising at the start"
    ),
    duration_source="Sec. 453-5.7.2 item 4 (24 hours); closing sentence (45 degrees F and rising)",
    safe_terminal_state=(
        "joint cured with the substrate held in the 40-95 degrees F band for the full 24 hours; "
        "no free moisture on the faces at any application step"
    ),
    interruption_permitted=(
        "NO; dropping below 40 degrees F inside the hold invalidates the jointing operation"
    ),
    failure_response=(
        "maintain the enclosure and the substrate band; if the band cannot be held, the operation "
        "must not proceed"
    ),
    recovery_duration_source=(
        "the 24 hours is itself the documented hold; no separate re-work duration is specified for "
        "a failed hold other than the Sec. 453-5.8 separate-clean-wait-24 h route"
    ),
    resource_hold_during_pause=(
        "DOCUMENTED: enclosure, heating plant, erection equipment contact pressure and crew are held "
        "for 24 hours"
    ),
    transfer_scope=(
        "gives the simulation a genuine multi-hour resource hold with a documented duration"
    ),
    sensitivity_range=(
        "sweep the hold 12 / 24 / 36 hours (24 h documented; 12 h and 36 h are stress-test values only)"
    ),
    reviewer_attack_risk=(
        "MEDIUM: the 24-hour hold binds resources for a day, so any simulated 'gain' from better "
        "forecasting could be an artefact of the hold model rather than of the forecast"
    ),
    mitigation=(
        "make the hold a first-class resource-occupancy constraint in the schedule model, not a "
        "cost penalty, and report results with the hold swept"
    ),
    evidence_grade="PRIMARY_OWNER_SPECIFICATION_TEXT_SEEN",
    open_issue="the artificial-heating route is optional, so the 24-hour hold applies only when it is elected",
    date_checked="2026-09-15",
)

# ---------------------------------------------------------------------------
# OP03 -- concrete placement / delivery (material temperature and weather)
# ---------------------------------------------------------------------------
add(
    contract_id="OP03_concrete_placement_delivery",
    source_id="S28",
    page_or_section="GB 50666-2011, Sec. 8.1.2; invoked again by Sec. 10.3.5",
    doc_locator_as_seen=(
        "GB 50666-2011 (Code for construction of concrete structures), Sec. 8.1.2: "
        "'混凝土拌合物入模温度不应低于5℃，且不应高于35℃。' (the temperature of the concrete "
        "mixture at placing shall not be lower than 5 degrees C and shall not be higher than "
        "35 degrees C). Sec. 10.3.5 refers back: '混凝土拌合物入模温度应符合本规范第8.1.2条的规定。' "
        "The Sec. 10.3.5 commentary states the 35 degrees C cap is consistent with Sec. 8.1.2."
    ),
    equipment_scope="cast-in-place and precast concrete, fresh concrete mixture",
    work_stage="concrete placement (placing into the form)",
    operation_phase="PLACING_TEMPERATURE_GATE",
    variable_name="concrete mixture temperature at placing (入模温度)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "measured in the fresh concrete mixture; explicitly NOT ambient air temperature. "
        "The commentary to Sec. 10.3.5 contrasts it with the ambient-temperature trigger in 10.1.2."
    ),
    temporal_support="at the moment of placing; a per-truck / per-placement measurement (Sec. 10.2.18)",
    averaging_interval="instantaneous mixture temperature; Sec. 10.2.18 requires measurement during placing",
    start_limit="5",
    continuation_limit="5",
    unit="degrees C",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "must hold for the whole continuous placement; Sec. 10.3.6 requires continuous placing in hot "
        "weather, and Sec. 10.2.10 requires the already-placed layer to stay at or above 2 degrees C "
        "before it is covered"
    ),
    duration_source="Sec. 10.2.10 (2 degrees C layer floor) and Sec. 10.3.6 (continuous placing)",
    safe_terminal_state=(
        "placed, compacted, and surface protected against wind, moisture loss and heat "
        "(Sec. 10.2.14, Sec. 10.3.8)"
    ),
    interruption_permitted=(
        "yes, but the placed layer temperature must not fall below 2 degrees C before covering "
        "(Sec. 10.2.10)"
    ),
    failure_response=(
        "5 degrees C is a lower bound on the mixture; the winter-concreting measures in Sec. 10.2 are "
        "the response (heated mixing water/aggregate, insulation, thermal calculation per JGJ/T 104)"
    ),
    recovery_duration_source=(
        "Sec. 10.2.12 ties strength development to a freezing-critical strength, not to a wait time; "
        "no wait duration is given for resuming placement"
    ),
    resource_hold_during_pause=(
        "the batching plant, trucks, pump and crew are held; Sec. 10.2.8 requires insulated transport "
        "and pump lines"
    ),
    transfer_scope=(
        "a national code-level numeric limit for a material property, given as a mandatory "
        "'shall not' clause"
    ),
    sensitivity_range=(
        "sweep the lower bound 2 / 5 / 10 degrees C (5 degrees C documented; 2 degrees C is the "
        "documented layer floor from Sec. 10.2.10, not the placing limit)"
    ),
    reviewer_attack_risk=(
        "HIGH if misused: a reviewer will note that the project cannot observe the in-mix temperature "
        "from a weather forecast, so this limit is NOT forecastable"
    ),
    mitigation=(
        "state explicitly that GB 50666 Sec. 8.1.2 is a material acceptance limit requiring a "
        "thermometer in the concrete, not a weather-variable threshold, and that the simulation can "
        "only use the Sec. 10.1.1 ambient trigger as its ex-ante signal"
    ),
    evidence_grade="PRIMARY_NATIONAL_CODE_TEXT_SEEN",
    open_issue=(
        "the governing quantity is measured inside the material and cannot be derived from a forecast; "
        "only the ambient trigger in OP03-winter-trigger is forecastable"
    ),
    date_checked="2026-09-15",
)

add(
    contract_id="OP03_concrete_placement_delivery",
    source_id="S28",
    page_or_section="GB 50666-2011, Sec. 10.1.1 and its commentary; Sec. 10.1.2",
    doc_locator_as_seen=(
        "GB 50666-2011 Sec. 10.1.1: '根据当地多年气象资料统计，当室外日平均气温连续5日稳定低于5℃时，"
        "应采取冬期施工措施；当室外日平均气温连续5日稳定高于5℃时，可解除冬期施工措施。' (when the "
        "outdoor daily mean air temperature is steadily below 5 degrees C for 5 consecutive days, "
        "winter construction measures shall be taken). Sec. 10.1.2: '当日平均气温达到30℃及以上时，"
        "应按高温施工要求采取措施。' (when the daily mean air temperature reaches 30 degrees C or "
        "above, hot-weather construction measures shall be taken). The Sec. 10.1.2 commentary records "
        "that the American definition is 24 degrees C, Japan and Australia 30 degrees C, and the "
        "Chinese railway guide 30 degrees C."
    ),
    equipment_scope="all concrete construction under GB 50666-2011",
    work_stage="calendar / regime selection for the whole concreting operation",
    operation_phase="REGIME_TRIGGER",
    variable_name="outdoor daily mean air temperature (winter and hot-weather triggers)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "outdoor air temperature per the local meteorological record; height not specified in the code"
    ),
    temporal_support=(
        "multi-day: 5 consecutive days for the winter trigger; 1 day for the hot-weather trigger"
    ),
    averaging_interval=(
        "daily mean air temperature, evaluated over 5 consecutive days (winter) or 1 day (hot weather)"
    ),
    start_limit="5",
    continuation_limit="5",
    unit="degrees C",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="5 consecutive days to enter or leave winter construction; 1 day for hot weather",
    duration_source=(
        "Sec. 10.1.1 states the 5-day rule verbatim; its commentary notes the phrase was imported "
        "from meteorological practice"
    ),
    safe_terminal_state="regime correctly selected; the matching Sec. 10.2 / 10.3 measures applied",
    interruption_permitted="yes; leaving the regime requires 5 consecutive days above 5 degrees C",
    failure_response=(
        "Sec. 10.1.1 also requires emergency protection if the temperature plunges below 0 degrees C "
        "before the concrete has reached its freezing-critical strength"
    ),
    recovery_duration_source=(
        "Sec. 10.1.1 gives the exit rule (5 consecutive days above 5 degrees C); no other recovery "
        "duration is given"
    ),
    resource_hold_during_pause="not applicable; this is a regime switch, not a pause",
    transfer_scope=(
        "the ONLY multi-day hysteresis trigger found. It maps directly onto a date-window weather "
        "state in the simulation and is the strongest ex-ante forecastable signal in this contract."
    ),
    sensitivity_range=(
        "sweep the trigger 3 / 5 / 7 consecutive days and 3 / 5 / 7 degrees C "
        "(5 days and 5 degrees C are documented; the others are stress tests only)"
    ),
    reviewer_attack_risk=(
        "MEDIUM: the 5-day persistence rule has hysteresis, so a forecasting method that ignores it "
        "will look artificially bad, and one tuned to it will look artificially good"
    ),
    mitigation=(
        "implement the trigger as an explicit state machine with entry and exit conditions and "
        "pre-register the entry/exit treatment; report the trigger sweep as a sensitivity axis"
    ),
    evidence_grade="PRIMARY_NATIONAL_CODE_TEXT_SEEN",
    open_issue="the code does not fix the meteorological station or the spatial averaging of the daily mean",
    date_checked="2026-09-15",
)

add(
    contract_id="OP03_concrete_placement_delivery",
    source_id="S28",
    page_or_section="GB 50666-2011, Sec. 10.2.7",
    doc_locator_as_seen=(
        "GB 50666-2011 Sec. 10.2.7: '混凝土拌合物的出机温度不宜低于10℃，入模温度不应低于5℃；"
        "预拌混凝土或需远距离运输的混凝土，混凝土拌合物的出机温度可根据距离经热工计算确定，"
        "但不宜低于15℃。' (the discharge temperature of the concrete mixture should not be below "
        "10 degrees C and the placing temperature shall not be below 5 degrees C; for ready-mixed or "
        "long-haul concrete the discharge temperature may be set by thermal calculation but should "
        "not be below 15 degrees C)."
    ),
    equipment_scope="concrete batching / delivery in winter construction",
    work_stage="batching and delivery",
    operation_phase="DELIVERY_TEMPERATURE_GATE",
    variable_name="concrete mixture discharge temperature (出机温度)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="measured at the batching plant discharge, in the mixture",
    temporal_support="per batch / per truck",
    averaging_interval="instantaneous mixture temperature",
    start_limit="10",
    continuation_limit="10",
    unit="degrees C",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="must hold for each delivered batch reaching the work face",
    duration_source="Sec. 10.2.7 sets the discharge floor; Sec. 10.2.8 requires insulation of transport",
    safe_terminal_state="placed concrete meeting the Sec. 8.1.2 placing window",
    interruption_permitted="not applicable",
    failure_response=(
        "use the thermal calculation route to raise the discharge temperature; for ready-mixed or "
        "long-haul concrete the floor rises to 15 degrees C"
    ),
    recovery_duration_source="not documented",
    resource_hold_during_pause="transport and pump resources insulated and held (Sec. 10.2.8)",
    transfer_scope=(
        "shows that the code links an upstream batch temperature to a downstream placing temperature; "
        "the simulation can only use the documented NOTE that at a 10 degrees C discharge temperature "
        "the placing temperature may reach only 5 degrees C after transport"
    ),
    sensitivity_range=(
        "sweep the delivery decay 0 / 2.5 / 5 degrees C between discharge and placing "
        "(the code's commentary states 10 to 5 degrees C but gives no decay law)"
    ),
    reviewer_attack_risk=(
        "HIGH: the code gives no thermal-decay model, so any simulated transport cooling is our "
        "construction, not a documented relation"
    ),
    mitigation=(
        "treat transport cooling as an explicitly labelled ASSUMED transfer function with a swept "
        "coefficient, and never present it as a code requirement"
    ),
    evidence_grade="PRIMARY_NATIONAL_CODE_TEXT_SEEN",
    open_issue="no documented transport-cooling law exists in the code; only the endpoint note does",
    date_checked="2026-09-15",
)

add(
    contract_id="OP03_concrete_placement_delivery",
    source_id="S28",
    page_or_section="GB 50666-2011, Sec. 10.4.4 and Sec. 10.4.6; commentary to Sec. 10.4.4",
    doc_locator_as_seen=(
        "GB 50666-2011 Sec. 10.4.4: '雨期施工期间，除应采用防护措施外，小雨、中雨天气不宜进行混凝土露天浇筑，"
        "且不应进行大面积作业的混凝土露天浇筑；大雨、暴雨天气不应进行混凝土露天浇筑。' Sec. 10.4.6: "
        "'模板内和混凝土浇筑分层面出现积水时，应在排水后再浇筑混凝土。' The Sec. 10.4.4 commentary adds "
        "that before placing the weather situation should be checked in good time."
    ),
    equipment_scope="open-air concrete placing",
    work_stage="open-air placement during rain periods",
    operation_phase="RAIN_GATE",
    variable_name="rainfall intensity category",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="not applicable (categorical weather state)",
    temporal_support="current and imminent rain state at the placing face",
    averaging_interval=(
        "NOT_NUMERIC: the code uses the Chinese rainfall categories 小雨/中雨 (light/moderate rain) "
        "and 大雨/暴雨 (heavy rain/rainstorm) and gives no mm/h boundary in this clause"
    ),
    start_limit="NO_NUMERIC_VALUE",
    continuation_limit="NO_NUMERIC_VALUE",
    unit="categorical (light/moderate vs heavy/rainstorm)",
    threshold_basis_DOCUMENTED_or_ASSUMED=(
        "DOCUMENTED as a rule; NO DOCUMENTED NUMERIC THRESHOLD (the mm/h boundaries come from the "
        "separate national rainfall-intensity standard, which was not obtained)"
    ),
    required_duration="not stated",
    duration_source="not stated in GB 50666-2011",
    safe_terminal_state=(
        "placing stopped, exposed concrete covered with plastic sheeting or equivalent (Sec. 10.4.9), "
        "formwork free of standing water (Sec. 10.4.6)"
    ),
    interruption_permitted="yes",
    failure_response=(
        "light/moderate rain: should not place in the open and shall not start large-area open-air "
        "placing; heavy rain/rainstorm: shall not place in the open"
    ),
    recovery_duration_source=(
        "Sec. 10.4.5 requires a post-rain settlement check of the foundation and of formwork and "
        "falsework and remedial action if settlement exceeds the standard, but gives no duration"
    ),
    resource_hold_during_pause=(
        "pump, crew and cover materials held; Sec. 10.4.3 requires rain protection of the placing face"
    ),
    transfer_scope=(
        "a categorical rather than numeric gate; usable only if the simulation adopts a documented "
        "mm/h mapping from a separate rainfall-intensity standard"
    ),
    sensitivity_range=(
        "do NOT sweep a fabricated mm/h boundary. Either adopt a cited rainfall-intensity standard "
        "or model this gate as a binary rain / no-rain indicator declared as ASSUMED."
    ),
    reviewer_attack_risk=(
        "HIGHEST single attack in this contract: the code's gate is categorical, so any mm/h number "
        "the paper uses would be invented"
    ),
    mitigation=(
        "keep the gate categorical, declare the mm/h conversion ASSUMED with its source flagged as "
        "not obtained, and run the main experiment with rain disabled and enabled to show it does not "
        "carry the result"
    ),
    evidence_grade="PRIMARY_NATIONAL_CODE_TEXT_SEEN",
    open_issue=(
        "no mm/h boundary in GB 50666-2011; GB/T 28591 (wind scale) was fetched but is image-only and "
        "the rainfall-intensity standard was not obtained"
    ),
    date_checked="2026-09-15",
)

add(
    contract_id="OP03_concrete_placement_delivery",
    source_id="S28",
    page_or_section="GB 50666-2011, Sec. 10.2.15, 10.2.16, 10.2.10, 10.2.14, 10.3.6",
    doc_locator_as_seen=(
        "Sec. 10.2.15 item 1: formwork and insulation may be removed only when the concrete has "
        "reached its freezing-critical strength and '混凝土表面温度不应高于5℃'. Sec. 10.2.16: '当混凝土"
        "表面温度与环境温度之差大于20℃时，拆模后的混凝土表面应立即进行保温覆盖。' Sec. 10.2.10: the "
        "already-placed layer '不得低于2℃' before being covered. Sec. 10.2.14 requires wind, moisture and "
        "heat protection of exposed surfaces after placing. Sec. 10.3.6 requires wind-break, shading "
        "and misting when the concrete moisture evaporation rate is high."
    ),
    equipment_scope="placed concrete, formwork stripping and curing",
    work_stage="curing and formwork removal (striking)",
    operation_phase="CURING_AND_STRIKING_GATE",
    variable_name="surface-to-ambient temperature difference and layer temperature",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="concrete surface temperature and ambient air temperature",
    temporal_support="during curing; until freezing-critical strength is reached",
    averaging_interval="instantaneous readings; Sec. 10.2.18 requires measurement of ambient and internal temperature",
    start_limit="20",
    continuation_limit="20",
    unit="degrees C (surface minus ambient difference)",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration=(
        "until the concrete reaches its freezing-critical strength, defined in Sec. 10.2.12 as a "
        "percentage of design strength or an absolute MPa value depending on the method and temperature"
    ),
    duration_source="Sec. 10.2.12 (strength), Sec. 10.2.16 (20 degrees C difference trigger)",
    safe_terminal_state=(
        "formwork removed only when surface temperature is not above 5 degrees C AND the "
        "freezing-critical strength is reached; immediate insulation cover if the difference exceeds "
        "20 degrees C"
    ),
    interruption_permitted="yes; curing must continue (Sec. 10.2.16) if the strength is not reached",
    failure_response="continue curing and keep the insulation in place",
    recovery_duration_source=(
        "no duration is given; the criterion is a strength criterion, not a time criterion"
    ),
    resource_hold_during_pause="the formwork, falsework and insulation are held",
    transfer_scope=(
        "important negative evidence: Chinese winter concreting is governed by STRENGTH criteria, "
        "not by a fixed number of hours, so it cannot supply a clean duration parameter"
    ),
    sensitivity_range=(
        "sweep the difference trigger 15 / 20 / 25 degrees C (20 degrees C documented)"
    ),
    reviewer_attack_risk=(
        "MEDIUM: a strength-based rather than time-based criterion forces the simulation to model "
        "maturity, which the current event engine does not do"
    ),
    mitigation=(
        "either implement a documented maturity/strength model or exclude the striking stage from the "
        "weather-sensitive task set and say so explicitly"
    ),
    evidence_grade="PRIMARY_NATIONAL_CODE_TEXT_SEEN",
    open_issue="converting a strength criterion into a task duration requires a maturity model that is not yet implemented",
    date_checked="2026-09-15",
)

# ---------------------------------------------------------------------------
# OP01-CN -- Chinese code-level numeric wind limits (independent jurisdiction)
# ---------------------------------------------------------------------------
add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S35",
    page_or_section="GB 55034-2022 Sec. 3.4.7",
    doc_locator_as_seen=(
        "GB 55034-2022《建筑与市政施工现场安全卫生与职业健康通用规范》Sec. 3.4.7: "
        "'大型起重机械严禁在雨、雪、雾、霾、沙尘等低能见度天气时进行安装拆卸作业；"
        "起重机械最高处的风速超过9.0m/s时，应停止起重机安装拆卸作业。' (large lifting machinery must "
        "not be installed or dismantled in rain, snow, fog, haze or dust; when the wind speed at the "
        "highest point of the machine exceeds 9.0 m/s, crane installation and dismantling must stop)"
    ),
    equipment_scope="large lifting machinery, installation and dismantling",
    work_stage="crane installation / dismantling (NOT normal lifting)",
    operation_phase="INSTALL_DISMANTLE_LIMIT",
    variable_name="wind speed at the highest point of the machine (安装拆卸)",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "起重机械最高处 -- at the highest point of the machine. This is a CODE-STATED height, which no "
        "manufacturer manual or European/UK source in this contract provides."
    ),
    temporal_support="at the moment of the installation/dismantling operation",
    averaging_interval="NOT_STATED_BY_THE_CODE",
    start_limit="9.0",
    continuation_limit="9.0",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated; a magnitude stop rule on a discrete operation",
    duration_source="the code sets no duration for the installation/dismantling operation",
    safe_terminal_state=(
        "installation/dismantling suspended, machinery left in a stable secured configuration; "
        "GB 5144-2006 Sec. 6.3.4/6.8 requires free slewing plus rail clamping in the non-working state"
    ),
    interruption_permitted="yes; a discrete operation that can be suspended and resumed",
    failure_response=(
        "stop the installation/dismantling operation. Low-visibility weather (rain, snow, fog, haze, "
        "dust) independently prohibits the operation regardless of wind speed."
    ),
    recovery_duration_source="not documented",
    resource_hold_during_pause="ASSUMED: the erection crew and crane hold",
    transfer_scope=(
        "STRONGEST SINGLE SOURCE in this contract. GB 55034-2022 is a 强制性工程建设规范 (full-text "
        "mandatory technical code): every clause is mandatory and it prevails over the older JGJ/GB "
        "standards. It is the only code-level numeric wind limit found in any jurisdiction in this search."
    ),
    sensitivity_range=(
        "sweep 7.0 / 9.0 / 12.0 m/s. 9.0 m/s is the mandatory code value; 12.0 m/s is JGJ 196-2010 "
        "Sec. 4.0.9 and GB 5144-2006 Sec. 10.2, which the newer mandatory code supersedes."
    ),
    reviewer_attack_risk=(
        "LOW for the value, HIGH for scope: this limit governs INSTALLATION AND DISMANTLING, not ordinary "
        "lifting. A reviewer will attack the paper if 9.0 m/s is presented as a normal-lifting threshold."
    ),
    mitigation=(
        "label the phase INSTALL_DISMANTLE_LIMIT; keep it strictly out of the main-lift start rule; and "
        "use it in the paper as independent code-level evidence that state-dependent wind contracts are "
        "real, not as an ordinary-lifting limit"
    ),
    evidence_grade="PRIMARY_MANDATORY_CODE_TEXT_SEEN",
    open_issue="the code states the height but not the averaging interval",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S36",
    page_or_section="JGJ 33-2012 Sec. 4.1.14 and Sec. 4.1.15; Ministry Announcement No. 1364",
    doc_locator_as_seen=(
        "JGJ 33-2012《建筑机械使用安全技术规程》Sec. 4.1.14: '在风速达到 9.0m/s 及以上或大雨、大雪、"
        "大雾等恶劣天气时，严禁进行建筑起重机械的安装拆卸作业。' Sec. 4.1.15: '在风速达到 12.0m/s 及以上"
        "或大雨、大雪、大雾等恶劣天气时，应停止露天的起重吊装作业。重新作业前，应先试吊，并应确认各种"
        "安全装置灵敏可靠后进行作业。' Ministry Announcement No. 1364 lists Sec. 4.1.14 among the "
        "mandatory clauses (强制性条文)."
    ),
    equipment_scope="construction lifting machinery (tower cranes, hoists, mobile cranes)",
    work_stage="open-air lifting (4.1.15) and installation/dismantling (4.1.14)",
    operation_phase="CODE_LEVEL_LIFT_LIMIT",
    variable_name="code-level wind speed limit for open-air lifting and for installation/dismantling",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "the clause text states no height for these two clauses; the Sec. 4.1.14 tiaowen shuoming defines "
        "风速 as '施工现场风速，包括地面和高耸设备高处风速' (site wind speed, including ground-level and "
        "elevated-equipment-height wind speed)"
    ),
    temporal_support="at the moment of the operation",
    averaging_interval="NOT_STATED_BY_THE_CODE",
    start_limit="9.0",
    continuation_limit="12.0",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated",
    duration_source=(
        "the code sets no duration, but Sec. 4.1.15 DOES impose a documented restart procedure: before "
        "resuming work, test-lift first and confirm every safety device is responsive and reliable"
    ),
    safe_terminal_state="lifting stopped; restart only after a documented trial lift and safety-device check",
    interruption_permitted="yes, with a documented restart procedure",
    failure_response=(
        "at 9.0 m/s installation/dismantling is prohibited; at 12.0 m/s open-air lifting must stop; "
        "heavy rain, heavy snow and heavy fog stop it independently of wind"
    ),
    recovery_duration_source=(
        "Sec. 4.1.15 requires a trial lift and a safety-device check before resuming, but states NO time. "
        "The project's restart delay therefore remains ASSUMED."
    ),
    resource_hold_during_pause="ASSUMED: crew and crane hold",
    transfer_scope=(
        "KEY FINDING for the paper's motivation: within ONE code, the installation/dismantling limit "
        "(9.0 m/s) is STRICTER than the open-air lifting limit (12.0 m/s). This is a real, citable, "
        "code-level instance of state-dependent wind limits. Caveat: they are two adjacent ACTIVITIES "
        "(dismantling vs production lifting), not two phases of one continuous activity, so this must NOT "
        "be described as a start/continuation asymmetry of a single operation."
    ),
    sensitivity_range="sweep the lifting limit 9.0 / 12.0 / 16.5 / 20 m/s across jurisdictions",
    reviewer_attack_risk=(
        "MEDIUM: 12 m/s is far more restrictive than the 20 m/s manufacturer rating used for OP01, so a "
        "reviewer will ask which one the paper actually believes. There is also an in-code inconsistency: "
        "GB 5144-2006 Sec. 10.2 allows 13 m/s for the same installation activity."
    ),
    mitigation=(
        "do not silently pick one. Present the cross-jurisdiction spread (12 m/s CN code, 16.5 m/s UK "
        "industry, 20 m/s manufacturer) as the reason the threshold is a SWEPT parameter, and report the "
        "main result across that spread"
    ),
    evidence_grade="PRIMARY_CODE_TEXT_SEEN",
    open_issue=(
        "no averaging interval; and the 12 m/s lifting limit is a Chinese industry-standard value that "
        "does not automatically transfer to a European site or crane"
    ),
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S36",
    page_or_section="JGJ 33-2012 Sec. 8.10.8 and its tiaowen shuoming",
    doc_locator_as_seen=(
        "JGJ 33-2012 Sec. 8.10.8: '当风速达到 10.8m/s 及以上或大雨、大雾等恶劣天气应停止作业。' "
        "(concrete placing boom: stop work at wind speed of 10.8 m/s or above, or in heavy rain or heavy "
        "fog). The clause commentary treats 10.8 m/s as the lower bound of the Beaufort force 6 no-work "
        "wind speed."
    ),
    equipment_scope="concrete placing boom / distributor (布料机)",
    work_stage="concrete placing",
    operation_phase="CONCRETE_PLACING_WIND_LIMIT",
    variable_name="wind speed limit for concrete placing with a boom",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="no height stated in this clause",
    temporal_support="at the moment of placing",
    averaging_interval="NOT_STATED_BY_THE_CODE",
    start_limit="10.8",
    continuation_limit="10.8",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated",
    duration_source="the clause sets no duration for the placing operation",
    safe_terminal_state="placing stopped, boom secured, concrete surface protected",
    interruption_permitted="yes",
    failure_response="stop work at 10.8 m/s or above, or in heavy rain or heavy fog",
    recovery_duration_source="not documented",
    resource_hold_during_pause="ASSUMED: pump, crew and concrete supply held",
    transfer_scope=(
        "the ONLY numeric WIND limit attached to a concrete-placing operation found in this search. It is "
        "an important negative result for OP03: the code limits the placing MACHINE by wind, but sets no "
        "numeric wind or evaporation limit on the concrete itself."
    ),
    sensitivity_range="sweep 10.8 / 12.0 m/s",
    reviewer_attack_risk=(
        "LOW-MEDIUM: it is a machine limit, not a material limit. Presenting it as a concrete-material "
        "weather restriction would be wrong."
    ),
    mitigation=(
        "label it a placing-BOOM limit and state explicitly that GB 50666-2011 provides no numeric wind or "
        "evaporation threshold for concrete material behaviour (Sec. 10.2.14 and Sec. 10.3.6 are "
        "qualitative only)"
    ),
    evidence_grade="PRIMARY_CODE_TEXT_SEEN",
    open_issue="no averaging interval; the clause is machine-specific, not material-specific",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S37",
    page_or_section="JGJ 196-2010 Sec. 3.4.8, Sec. 4.0.9, Sec. 4.0.16 and Sec. 2 scope commentary",
    doc_locator_as_seen=(
        "JGJ 196-2010《建筑施工塔式起重机安装、使用、拆卸安全技术规程》Sec. 3.4.8: tower-crane "
        "installation (and dismantling via Sec. 5.0.4) requires the wind speed at the maximum height to be "
        "no greater than 12 m/s. Sec. 4.0.9: at 12 m/s or above, work must stop (normal use). Sec. 4.0.16: "
        "obstruction lights above 30 m; an anemometer is required when the jib root hinge point is above "
        "50 m. Sec. 2 commentary: '顶升、加节、降节等工作均属于安装、拆卸范畴' (jacking, adding sections and "
        "removing sections all fall within the scope of installation and dismantling)."
    ),
    equipment_scope="tower cranes specifically",
    work_stage="installation/dismantling (incl. jacking and section changes) and normal use",
    operation_phase="TOWER_CRANE_SCOPED_LIMIT",
    variable_name="tower-crane wind speed limit at maximum height",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "最大高度处风速 / 最大安装高度处 -- wind speed at the maximum (installation) height of the machine. "
        "Anemometer required when the jib root hinge point is above 50 m."
    ),
    temporal_support="at the moment of the operation",
    averaging_interval="NOT_STATED_BY_THE_CODE",
    start_limit="12.0",
    continuation_limit="12.0",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated",
    duration_source="the code sets no duration",
    safe_terminal_state="operation stopped; anemometer monitoring continues",
    interruption_permitted="yes",
    failure_response="at 12 m/s or above, stop the operation",
    recovery_duration_source="not documented",
    resource_hold_during_pause="ASSUMED: crew and crane hold",
    transfer_scope=(
        "the only tower-crane-SPECIFIC code source found, and the only one that rules on scope: jacking and "
        "section changes are installation/dismantling, not normal use. That scope ruling is what makes the "
        "strICter 9.0 m/s mandatory limit in GB 55034-2022 applicable to climbing work."
    ),
    sensitivity_range="sweep 9.0 / 12.0 / 13.0 m/s (GB 55034-2022 / JGJ 196-2010 / GB 5144-2006)",
    reviewer_attack_risk=(
        "MEDIUM: three Chinese sources give three different numbers (9.0 mandatory, 12.0, 13.0). A reviewer "
        "can read that as the project cherry-picking."
    ),
    mitigation=(
        "state the code hierarchy explicitly: GB 55034-2022 is the later full-text mandatory code and "
        "prevails, so 9.0 m/s governs installation/dismantling; 12 and 13 m/s are recorded as superseded "
        "values and are used only as sensitivity bounds, never as the chosen limit"
    ),
    evidence_grade="PRIMARY_CODE_TEXT_SEEN",
    open_issue="no averaging interval; JGJ 196-2010 predates GB 55034-2022 and is partially superseded",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S39",
    page_or_section="GB 6067.1-2010 Sec. 9.6.1.1, Sec. 9.6.1.2 and Sec. 17.1 k)",
    doc_locator_as_seen=(
        "GB 6067.1-2010《起重机械安全规程 第1部分：总则》Sec. 9.6.1.1: an anemometer must be installed on "
        "tall outdoor cranes at the windward position on the upper part of the crane. Sec. 9.6.1.2: tall "
        "outdoor cranes must have a wind alarm displaying 瞬时风速 (INSTANTANEOUS wind speed), alarming when "
        "the wind force exceeds the working-state design wind speed. Sec. 17.1 k): operation is not "
        "permitted when the wind speed exceeds the maximum working wind speed specified by the manufacturer."
    ),
    equipment_scope="lifting appliances generally",
    work_stage="in-service operation and annunciation",
    operation_phase="MEASUREMENT_SEMANTICS",
    variable_name="what the code's wind alarm actually measures",
    measurement_height="see measurement_height_reference",
    measurement_height_reference=(
        "anemometer at the windward position on the upper part of the crane (Sec. 9.6.1.1) -- a "
        "code-stated MOUNTING POSITION, though not an exact height"
    ),
    temporal_support="instantaneous",
    averaging_interval=(
        "INSTANTANEOUS wind speed (瞬时风速) per Sec. 9.6.1.2. This is the single most useful semantic "
        "finding in the whole search: the governing accident-prevention quantity in the Chinese lifting "
        "code chain is instantaneous, NOT a 10-minute mean."
    ),
    start_limit="NO_CODE_NUMBER",
    continuation_limit="NO_CODE_NUMBER",
    unit="n/a (semantics row)",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not applicable",
    duration_source="not applicable",
    safe_terminal_state="not applicable; this row fixes measurement semantics only",
    interruption_permitted="not applicable",
    failure_response=(
        "Sec. 17.1 k) prohibits operation above the manufacturer's maximum working wind speed, so the code "
        "again delegates the number rather than fixing one"
    ),
    recovery_duration_source="not applicable",
    resource_hold_during_pause="not applicable",
    transfer_scope=(
        "resolves the averaging-interval question in the NEGATIVE direction: three of the four crane-wind "
        "code families examined (CN instantaneous, DE delegated, US delegated) imply or state a "
        "short-duration quantity, and none states a 10-minute mean. This strengthens the conservative "
        "'treat the forecast gust as governing' default."
    ),
    sensitivity_range="not a numeric parameter; informs the avg_interval_treatment axis",
    reviewer_attack_risk=(
        "LOW as evidence. The risk is the opposite: over-reading it as proof that a 3-second gust is "
        "governing, which the code does NOT say."
    ),
    mitigation=(
        "state precisely what is documented (the alarm displays instantaneous wind speed) and what is not "
        "(no code specifies a 3-second or 10-minute averaging window for the LIMIT). A draft standard is "
        "recorded separately at S42 and must not be cited as binding"
    ),
    evidence_grade="PRIMARY_CODE_TEXT_SEEN",
    open_issue="instantaneous display does not by itself define the averaging window of the limit value",
    date_checked="2026-09-15",
)

add(
    contract_id="OP01_tower_crane_segment_lift_CN",
    source_id="S40",
    page_or_section="JGJ 80-2016 Sec. 3.0.8 and its tiaowen shuoming",
    doc_locator_as_seen=(
        "JGJ 80-2016《建筑施工高处作业安全技术规范》Sec. 3.0.8: work at height in the open -- climbing and "
        "suspended work -- must not be carried out in Beaufort force 6 or stronger wind, dense fog or "
        "sandstorm. The code's own commentary states: '6级以上强风指风速超过10.8m/s~13.8m/s的风' (wind of "
        "Beaufort force 6 or above means wind whose speed exceeds 10.8 m/s to 13.8 m/s)."
    ),
    equipment_scope="all open-air work at height (not crane-specific)",
    work_stage="climbing and suspended work at height",
    operation_phase="WORK_AT_HEIGHT_STOP",
    variable_name="Beaufort-force-based stop rule for work at height",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="site wind speed; no height stated for this clause",
    temporal_support="at the moment of the work",
    averaging_interval=(
        "the code uses a Beaufort FORCE, which the Met Office (S30) defines on a mean wind speed with a "
        "stated limit band. The code's own conversion is 10.8-13.8 m/s."
    ),
    start_limit="10.8",
    continuation_limit="13.8",
    unit="m/s (code's own conversion of Beaufort force 6)",
    threshold_basis_DOCUMENTED_or_ASSUMED="DOCUMENTED",
    required_duration="not stated",
    duration_source="the code sets no duration",
    safe_terminal_state="work at height stopped; personnel descend or are secured",
    interruption_permitted="yes; work at height is intermittent by nature",
    failure_response="do not carry out open-air climbing or suspended work at height",
    recovery_duration_source="not documented",
    resource_hold_during_pause="ASSUMED: crew held or redeployed",
    transfer_scope=(
        "the BROADEST scope of any wind stop rule found: it stops the work at height itself rather than a "
        "specific machine, and it is the only source that converts a Beaufort force to m/s inside the code "
        "itself. Its 10.8 m/s lower bound coincides exactly with JGJ 33-2012 Sec. 8.10.8 and with the "
        "Standard's Table 4-2 lower bound for force 6."
    ),
    sensitivity_range=(
        "the code's own band is 10.8-13.8 m/s. Using 10.8 (the lower bound) is the conservative choice."
    ),
    reviewer_attack_risk=(
        "LOW: the code supplies its own conversion. The residual risk is that a Beaufort FORCE is defined "
        "on a MEAN wind speed (S30), so this is the one Chinese rule that is arguably mean-based rather "
        "than gust-based -- the opposite of S39's instantaneous alarm."
    ),
    mitigation=(
        "use the code's own conservative lower bound 10.8 m/s, note that force 6 is mean-defined, and keep "
        "this in the sensitivity axis rather than as the primary lifting threshold"
    ),
    evidence_grade="PRIMARY_CODE_TEXT_SEEN",
    open_issue=(
        "Beaufort force is mean-defined while the crane alarm in S39 is instantaneous; the two Chinese "
        "rules therefore rest on different averaging conventions"
    ),
    date_checked="2026-09-15",
)

# ---------------------------------------------------------------------------
# OP04 -- retained baseline (HS2), kept for traceability only
# ---------------------------------------------------------------------------
add(
    contract_id="HS2_segment_installation_BASELINE_ONLY",
    source_id="S05",
    page_or_section="HS2 Learning Legacy technical account, lifting operations paragraph",
    doc_locator_as_seen=(
        "HS2 Learning Legacy, 'A weather-resilient approach to construction: Lessons from Align Joint "
        "Venture on HS2' (S05); thresholds as previously extracted into "
        "outputs/operation_contract_details.csv and outputs/hs2_extracted.txt in this project"
    ),
    equipment_scope="Align JV launch girder, Colne Valley Viaduct paired deck-segment installation",
    work_stage="paired deck-segment installation",
    operation_phase="MAIN_LIFT",
    variable_name="gust wind speed",
    measurement_height="see measurement_height_reference",
    measurement_height_reference="NOT_ESTABLISHED",
    temporal_support="NOT_ESTABLISHED",
    averaging_interval="NOT_ESTABLISHED",
    start_limit="11.1",
    continuation_limit="20",
    unit="m/s",
    threshold_basis_DOCUMENTED_or_ASSUMED=(
        "DOCUMENTED but secondary: a case-specific operational account, not a manufacturer manual or "
        "a standard"
    ),
    required_duration="NOT_ESTABLISHED",
    duration_source="NOT_ESTABLISHED",
    safe_terminal_state="segment safely installed, then girder anchored where above-20 m/s winds are expected",
    interruption_permitted="source states it is safer to finish than to restart",
    failure_response="NOT_ESTABLISHED above the continuation limit",
    recovery_duration_source="NOT_ESTABLISHED",
    resource_hold_during_pause="NOT_ESTABLISHED",
    transfer_scope=(
        "RETAINED AS MOTIVATION ONLY. Do not apply 11.1/20 m/s to any crane; that warning is already "
        "recorded in protocol/AiC_详细执行方案_中文.md Sec. 3.1."
    ),
    sensitivity_range="not swept; this row is not used to generate any experimental result",
    reviewer_attack_risk=(
        "HIGH if reused: the numbers have no stated instrument, height, averaging interval or "
        "duration, and a reviewer will call them arbitrary"
    ),
    mitigation=(
        "keep this row in the table but exclude it from the machine-readable contract; OP01 source_id "
        "S23 (a manufacturer manual) and S24 (a trade-body recommendation) replace it"
    ),
    evidence_grade="SECONDARY_CASE_ACCOUNT_NOT_ESTABLISHED",
    open_issue="superseded by OP01; retained only to show that the weak gate G2 has been closed",
    date_checked="2026-09-15",
)


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    tag_evidence_class()
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"wrote {OUT_CSV} rows={len(ROWS)} cols={len(COLUMNS)}")
    contracts = sorted({r["contract_id"] for r in ROWS})
    print("contracts:", contracts)
    for cls in ("DOCUMENTED_LIMIT", "DOCUMENTED_LIMIT_OUR_ARITHMETIC", "DOCUMENTED_PROCEDURE", "NOT_OBTAINABLE"):
        n = sum(1 for r in ROWS if r["evidence_class"] == cls)
        print(f"  {cls}: {n}")


if __name__ == "__main__":
    main()
