"""
JDE EnterpriseOne 9.2 - Manufacturing Module Data Model
Covers: Work Orders, BOMs, Routings, MRP, Shop Floor, Costing
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class JDEField:
    alias: str          # JDE data dictionary alias (e.g. DOCO)
    name: str           # Human name
    data_type: str      # STRING | MATH_NUMERIC | JDEDATE
    description: str


@dataclass
class JDETable:
    name: str           # Table name e.g. F4801
    description: str
    module: str
    fields: List[JDEField]
    key_fields: List[str]
    related_tables: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# WORK ORDER MANAGEMENT (Module 48)
# ─────────────────────────────────────────────────────────────────────────────

F4801 = JDETable(
    name="F4801",
    description="Work Order Master File — main work order header record",
    module="Work Orders",
    key_fields=["DOCO", "DCTO", "KCOO"],
    related_tables=["F4801T", "F4802", "F3111", "F3112", "F3116"],
    fields=[
        JDEField("DOCO",  "Work Order Number",          "MATH_NUMERIC", "Unique work order document number"),
        JDEField("DCTO",  "Document Type",              "STRING",        "WO = Work Order, WR = Rework, etc."),
        JDEField("KCOO",  "Company (Key)",              "STRING",        "Company number for the work order"),
        JDEField("MCU",   "Business Unit / Plant",      "STRING",        "Manufacturing plant or cost center"),
        JDEField("ITM",   "Item Number (short)",        "MATH_NUMERIC", "Short item number of item being produced"),
        JDEField("LITM",  "Item Number (2nd)",          "STRING",        "Second item number (customer item)"),
        JDEField("AITM",  "Item Number (3rd)",          "STRING",        "Third item number (supplier item)"),
        JDEField("LOTN",  "Lot Number",                 "STRING",        "Lot/serial number for the finished good"),
        JDEField("LOCN",  "Location",                   "STRING",        "Warehouse location for completion"),
        JDEField("UORG",  "Quantity Ordered",           "MATH_NUMERIC", "Original quantity ordered on work order"),
        JDEField("SOQS",  "Quantity Scrapped",          "MATH_NUMERIC", "Total quantity scrapped"),
        JDEField("TRQT",  "Quantity Completed",         "MATH_NUMERIC", "Quantity completed/received"),
        JDEField("UOM",   "Unit of Measure",            "STRING",        "Primary unit of measure"),
        JDEField("DRQJ",  "Requested Date",             "JDEDATE",       "Date work order is needed"),
        JDEField("STRT",  "Start Date",                 "JDEDATE",       "Planned start date"),
        JDEField("SETK",  "Completion Date",            "JDEDATE",       "Planned completion date"),
        JDEField("SRST",  "Status",                     "STRING",        "10=Entered,20=Approved,30=Released,40=In Process,90=Complete,99=Closed"),
        JDEField("ORST",  "Original Status",            "STRING",        "Status at time of creation"),
        JDEField("BREV",  "BOM Revision Level",         "STRING",        "Bill of Material revision used"),
        JDEField("RREV",  "Routing Revision Level",     "STRING",        "Routing revision used"),
        JDEField("MMCU",  "From Business Unit",         "STRING",        "Source plant for transfer orders"),
        JDEField("PRSC",  "Priority",                   "STRING",        "WO scheduling priority"),
        JDEField("RSCD",  "Reason Code",                "STRING",        "Reason for the work order"),
        JDEField("APID",  "Approved By",                "STRING",        "User ID who approved the WO"),
        JDEField("PRIO",  "Priority Code",              "STRING",        "Production priority"),
        JDEField("FUCO",  "Future Cost",                "MATH_NUMERIC", "Estimated future cost"),
        JDEField("ECST",  "Estimated Cost",             "MATH_NUMERIC", "Total estimated cost"),
        JDEField("ACST",  "Actual Cost",                "MATH_NUMERIC", "Total actual cost to date"),
        JDEField("VNDG",  "Work Center",                "STRING",        "Primary work center for production"),
        JDEField("CWUN",  "Completed Work Units",       "MATH_NUMERIC", "Units completed through operations"),
        JDEField("USER",  "User ID",                    "STRING",        "User who created the record"),
        JDEField("UPMJ",  "Last Updated Date",          "JDEDATE",       "Date record was last modified"),
    ]
)

F4801T = JDETable(
    name="F4801T",
    description="Work Order Text — extended description and notes for work orders",
    module="Work Orders",
    key_fields=["DOCO", "DCTO", "KCOO", "LNID"],
    related_tables=["F4801"],
    fields=[
        JDEField("DOCO", "Work Order Number", "MATH_NUMERIC", "Work order document number"),
        JDEField("DCTO", "Document Type",     "STRING",        "Work order document type"),
        JDEField("KCOO", "Company",           "STRING",        "Company key"),
        JDEField("LNID", "Line Number",       "MATH_NUMERIC", "Text line sequence number"),
        JDEField("TXT",  "Text",              "STRING",        "Work order notes / instructions"),
    ]
)

F4802 = JDETable(
    name="F4802",
    description="Work Order Parts List — components issued or required for a work order",
    module="Work Orders",
    key_fields=["DOCO", "DCTO", "KCOO", "CPNT"],
    related_tables=["F4801", "F4101", "F0911"],
    fields=[
        JDEField("DOCO",  "Work Order Number",     "MATH_NUMERIC", "Parent work order number"),
        JDEField("DCTO",  "Document Type",         "STRING",        "Work order type"),
        JDEField("KCOO",  "Company",               "STRING",        "Company key"),
        JDEField("CPNT",  "Component Item (short)","MATH_NUMERIC", "Short item number of component"),
        JDEField("LNID",  "Line Number",           "MATH_NUMERIC", "Parts list line sequence"),
        JDEField("LITM",  "Component Item (2nd)",  "STRING",        "Second item number of component"),
        JDEField("LOTN",  "Lot Number",            "STRING",        "Lot number of component"),
        JDEField("LOCN",  "Location",              "STRING",        "Warehouse location for component"),
        JDEField("MCU",   "Business Unit",         "STRING",        "Plant/branch for component"),
        JDEField("TRQT",  "Quantity Required",     "MATH_NUMERIC", "Total quantity required"),
        JDEField("ISQT",  "Quantity Issued",       "MATH_NUMERIC", "Quantity actually issued"),
        JDEField("SQOR",  "Quantity Scrapped",     "MATH_NUMERIC", "Component quantity scrapped"),
        JDEField("UOM",   "Unit of Measure",       "STRING",        "Component UOM"),
        JDEField("OPSC",  "Operation Sequence",    "MATH_NUMERIC", "Routing operation where component is used"),
        JDEField("BQTY",  "Backflush Quantity",    "MATH_NUMERIC", "Quantity to backflush"),
        JDEField("CPNB",  "Component Line Type",  "STRING",        "S=Stock,N=Non-stock,T=Text,F=Featurecost"),
        JDEField("ECST",  "Estimated Cost",        "MATH_NUMERIC", "Estimated component cost"),
        JDEField("ACST",  "Actual Cost",           "MATH_NUMERIC", "Actual cost of issued components"),
        JDEField("UPMJ",  "Last Updated Date",     "JDEDATE",       "Date record last modified"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# BILL OF MATERIALS (Module 30)
# ─────────────────────────────────────────────────────────────────────────────

F3002 = JDETable(
    name="F3002",
    description="Bill of Material Master — defines components for each manufactured item",
    module="Bill of Materials",
    key_fields=["KIT", "MMCU", "BREV", "CPNT", "OPSC"],
    related_tables=["F4101", "F3003", "F3112"],
    fields=[
        JDEField("KIT",   "Parent Item (short)",      "MATH_NUMERIC", "Short item number of the parent/finished good"),
        JDEField("LKITL", "Parent Item (2nd)",        "STRING",        "Second item number of parent"),
        JDEField("MMCU",  "Branch/Plant",             "STRING",        "Manufacturing branch or plant"),
        JDEField("BREV",  "BOM Revision Level",       "STRING",        "Revision level of the BOM"),
        JDEField("CPNT",  "Component Item (short)",   "MATH_NUMERIC", "Short item number of component"),
        JDEField("LITM",  "Component Item (2nd)",     "STRING",        "Second item number of component"),
        JDEField("OPSC",  "Operation Sequence",       "MATH_NUMERIC", "Operation where component is consumed"),
        JDEField("LNID",  "Line Number",              "MATH_NUMERIC", "BOM line sequence number"),
        JDEField("BQTY",  "Component Quantity",       "MATH_NUMERIC", "Quantity of component per parent"),
        JDEField("UOM",   "Unit of Measure",          "STRING",        "Component unit of measure"),
        JDEField("EFFF",  "Effective From Date",      "JDEDATE",       "Date component becomes effective"),
        JDEField("EFFT",  "Effective Thru Date",      "JDEDATE",       "Date component expires"),
        JDEField("CPNB",  "Component Line Type",      "STRING",        "S=Stock,N=Non-stock,T=Text,W=Sub-assembly"),
        JDEField("SCRAP", "Scrap Percentage",         "MATH_NUMERIC", "Expected scrap % for this component"),
        JDEField("FCOST", "Fixed/Variable",           "STRING",        "F=Fixed quantity,V=Variable with order qty"),
        JDEField("FEAT",  "Feature",                  "STRING",        "Feature/option code for configurator"),
        JDEField("STKT",  "Stocking Type",            "STRING",        "Component stocking type"),
        JDEField("USER",  "User ID",                  "STRING",        "Who last updated this BOM line"),
        JDEField("UPMJ",  "Last Updated Date",        "JDEDATE",       "Date BOM line was last modified"),
    ]
)

F3003 = JDETable(
    name="F3003",
    description="Routing Master — operations and work centers required to produce an item",
    module="Routings",
    key_fields=["MMCU", "ITM", "RREV", "OPSC"],
    related_tables=["F3006", "F3002", "F4801"],
    fields=[
        JDEField("MMCU",  "Branch/Plant",             "STRING",        "Manufacturing plant"),
        JDEField("ITM",   "Item Number (short)",      "MATH_NUMERIC", "Short item number of manufactured item"),
        JDEField("LITM",  "Item Number (2nd)",        "STRING",        "Second item number"),
        JDEField("RREV",  "Routing Revision Level",   "STRING",        "Routing revision level"),
        JDEField("OPSC",  "Operation Sequence",       "MATH_NUMERIC", "Step number in the routing (10,20,30…)"),
        JDEField("OPDS",  "Operation Description",    "STRING",        "Description of the operation"),
        JDEField("WRKT",  "Work Center",              "STRING",        "Work center performing the operation"),
        JDEField("SETL",  "Setup Labor Hours",        "MATH_NUMERIC", "Hours to set up the operation"),
        JDEField("RUNL",  "Run Labor Hours",          "MATH_NUMERIC", "Labor hours per unit produced"),
        JDEField("MCHT",  "Machine Hours",            "MATH_NUMERIC", "Machine hours per unit produced"),
        JDEField("PRST",  "Crew Size",                "MATH_NUMERIC", "Number of operators at this operation"),
        JDEField("EFFF",  "Effective From Date",      "JDEDATE",       "Date routing step becomes effective"),
        JDEField("EFFT",  "Effective Thru Date",      "JDEDATE",       "Date routing step expires"),
        JDEField("SCRAP", "Scrap %",                  "MATH_NUMERIC", "Expected scrap at this operation"),
        JDEField("MOVD",  "Move Hours",               "MATH_NUMERIC", "Hours to move parts to next operation"),
        JDEField("QUEU",  "Queue Hours",              "MATH_NUMERIC", "Hours waiting in queue at this operation"),
        JDEField("OUTQ",  "Output Queue Hours",       "MATH_NUMERIC", "Queue hours after this operation"),
        JDEField("OPST",  "Operation Status",         "STRING",        "Status of operation on a work order"),
    ]
)

F3006 = JDETable(
    name="F3006",
    description="Work Center Master — defines work centers, capacities and rates",
    module="Routings",
    key_fields=["MMCU", "WRKT"],
    related_tables=["F3003", "F30006"],
    fields=[
        JDEField("MMCU",  "Branch/Plant",             "STRING",        "Manufacturing plant"),
        JDEField("WRKT",  "Work Center",              "STRING",        "Work center identifier"),
        JDEField("MDES",  "Description",              "STRING",        "Work center description"),
        JDEField("WCTP",  "Work Center Type",         "STRING",        "M=Machine,L=Labor,S=Subcontract"),
        JDEField("WCEF",  "Efficiency %",             "MATH_NUMERIC", "Work center efficiency percentage"),
        JDEField("WCUL",  "Utilization %",            "MATH_NUMERIC", "Work center utilization percentage"),
        JDEField("SHFT",  "Shifts per Day",           "MATH_NUMERIC", "Number of shifts this work center runs"),
        JDEField("HOUR",  "Hours per Shift",          "MATH_NUMERIC", "Available hours per shift"),
        JDEField("CREW",  "Crew Size",                "MATH_NUMERIC", "Default crew size"),
        JDEField("SETC",  "Setup Cost Rate",          "MATH_NUMERIC", "Cost rate for setup time"),
        JDEField("RUNC",  "Run Labor Rate",           "MATH_NUMERIC", "Cost rate for run labor"),
        JDEField("MCHC",  "Machine Cost Rate",        "MATH_NUMERIC", "Cost rate for machine time"),
        JDEField("OVHD",  "Overhead Rate",            "MATH_NUMERIC", "Overhead absorption rate"),
        JDEField("DWNM",  "Downtime %",               "MATH_NUMERIC", "Planned downtime percentage"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# SHOP FLOOR CONTROL (Module 31)
# ─────────────────────────────────────────────────────────────────────────────

F3111 = JDETable(
    name="F3111",
    description="Work Order Routing Instructions — routing operations and raw materials on a work order",
    module="Shop Floor",
    key_fields=["DOCO", "DCTO", "KCOO", "OPSC"],
    related_tables=["F4801", "F3112", "F3006"],
    fields=[
        JDEField("DOCO",  "Work Order Number",                    "MATH_NUMERIC", "Work order document number"),
        JDEField("DCTO",  "Document Type",                        "STRING",        "Work order document type"),
        JDEField("KCOO",  "Company",                              "STRING",        "Company key"),
        JDEField("OPSC",  "Operation Sequence",                   "MATH_NUMERIC", "Routing step number"),
        JDEField("OPDS",  "Operation Description",                "STRING",        "Description of this operation"),
        JDEField("WRKT",  "Work Center",                          "STRING",        "Work center assigned to operation"),
        JDEField("OPST",  "Operation Status",                     "STRING",        "10=Open,20=In Process,90=Complete"),
        JDEField("CPIT",  "Component Item Number - Short",        "MATH_NUMERIC", "Raw material / component item number"),
        JDEField("UORG",  "Units - Order/Transaction Quantity",   "MATH_NUMERIC", "Quantity of raw material required"),
        JDEField("SETL",  "Setup Hours Planned",                  "MATH_NUMERIC", "Planned setup hours"),
        JDEField("RUNL",  "Run Hours Planned",                    "MATH_NUMERIC", "Planned run hours per unit"),
        JDEField("MCHT",  "Machine Hours Planned",                "MATH_NUMERIC", "Planned machine hours"),
        JDEField("ASET",  "Actual Setup Hours",                   "MATH_NUMERIC", "Actual setup hours recorded"),
        JDEField("ARUN",  "Actual Run Hours",                     "MATH_NUMERIC", "Actual run labor hours"),
        JDEField("AMCH",  "Actual Machine Hours",                 "MATH_NUMERIC", "Actual machine hours"),
        JDEField("TRQT",  "Quantity to Run",                      "MATH_NUMERIC", "Quantity to process at this operation"),
        JDEField("SQOR",  "Quantity Scrapped",                    "MATH_NUMERIC", "Quantity scrapped at this operation"),
        JDEField("STRT",  "Planned Start Date",                   "JDEDATE",       "Scheduled start date for operation"),
        JDEField("DRQJ",  "Planned End Date",                     "JDEDATE",       "Scheduled end date for operation"),
        JDEField("ASTRT", "Actual Start Date",                    "JDEDATE",       "Actual start date"),
        JDEField("AEND",  "Actual End Date",                      "JDEDATE",       "Actual completion date"),
    ]
)

F3112 = JDETable(
    name="F3112",
    description="Work Order Time Transactions — labor and machine time recorded against work orders",
    module="Shop Floor",
    key_fields=["DOCO", "DCTO", "KCOO", "OPSC", "TRDJ"],
    related_tables=["F3111", "F4801", "F0901"],
    fields=[
        JDEField("DOCO",  "Work Order Number",        "MATH_NUMERIC", "Work order number"),
        JDEField("DCTO",  "Document Type",            "STRING",        "Document type"),
        JDEField("KCOO",  "Company",                  "STRING",        "Company key"),
        JDEField("OPSC",  "Operation Sequence",       "MATH_NUMERIC", "Operation sequence number"),
        JDEField("TRDJ",  "Transaction Date",         "JDEDATE",       "Date time was reported"),
        JDEField("WRKT",  "Work Center",              "STRING",        "Work center where time was reported"),
        JDEField("TYTN",  "Time Type",                "STRING",        "S=Setup,R=Run,M=Machine,O=Overhead"),
        JDEField("SETL",  "Setup Hours",              "MATH_NUMERIC", "Setup hours reported"),
        JDEField("RUNL",  "Run Hours",                "MATH_NUMERIC", "Run labor hours reported"),
        JDEField("MCHT",  "Machine Hours",            "MATH_NUMERIC", "Machine hours reported"),
        JDEField("TRQT",  "Quantity Completed",       "MATH_NUMERIC", "Quantity completed with this transaction"),
        JDEField("SQOR",  "Quantity Scrapped",        "MATH_NUMERIC", "Quantity scrapped"),
        JDEField("AN8",   "Employee Number",          "MATH_NUMERIC", "Employee who reported time"),
        JDEField("ECST",  "Estimated Cost",           "MATH_NUMERIC", "Estimated cost of labor"),
        JDEField("ACST",  "Actual Cost",              "MATH_NUMERIC", "Actual cost recorded"),
        JDEField("USER",  "User ID",                  "STRING",        "User who entered transaction"),
        JDEField("UPMJ",  "Last Updated Date",        "JDEDATE",       "Date last modified"),
    ]
)

F3116 = JDETable(
    name="F3116",
    description="Work Order Completions — records of finished goods received from work orders",
    module="Shop Floor",
    key_fields=["DOCO", "DCTO", "KCOO", "TRDJ", "LNID"],
    related_tables=["F4801", "F41021", "F0911"],
    fields=[
        JDEField("DOCO",  "Work Order Number",        "MATH_NUMERIC", "Work order document number"),
        JDEField("DCTO",  "Document Type",            "STRING",        "Work order type"),
        JDEField("KCOO",  "Company",                  "STRING",        "Company key"),
        JDEField("TRDJ",  "Transaction Date",         "JDEDATE",       "Completion date"),
        JDEField("LNID",  "Line Number",              "MATH_NUMERIC", "Completion line sequence"),
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Finished good item number"),
        JDEField("LOTN",  "Lot Number",               "STRING",        "Completed lot/serial number"),
        JDEField("LOCN",  "Location",                 "STRING",        "Location received into"),
        JDEField("MCU",   "Business Unit",            "STRING",        "Plant/warehouse"),
        JDEField("TRQT",  "Quantity Completed",       "MATH_NUMERIC", "Quantity received as complete"),
        JDEField("SQOR",  "Quantity Scrapped",        "MATH_NUMERIC", "Quantity scrapped on completion"),
        JDEField("UOM",   "Unit of Measure",          "STRING",        "UOM of completion quantity"),
        JDEField("ACST",  "Actual Cost",              "MATH_NUMERIC", "Cost of completed units"),
        JDEField("USER",  "User ID",                  "STRING",        "User who posted completion"),
        JDEField("UPMJ",  "Last Updated Date",        "JDEDATE",       "Date last modified"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# MRP / PLANNING (Module 34)
# ─────────────────────────────────────────────────────────────────────────────

F3411 = JDETable(
    name="F3411",
    description="MRP/MPS Detail Message File — planning messages generated by MRP run",
    module="MRP / Planning",
    key_fields=["ITM", "MMCU", "TRDJ", "MNID"],
    related_tables=["F4101", "F4801", "F4311"],
    fields=[
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Item being planned"),
        JDEField("MMCU",  "Branch/Plant",             "STRING",        "Planning plant"),
        JDEField("TRDJ",  "Date",                     "JDEDATE",       "Date of the planning message"),
        JDEField("MNID",  "Message ID",               "MATH_NUMERIC", "Unique message identifier"),
        JDEField("MSGN",  "Message Number",           "STRING",        "Message type code"),
        JDEField("MSGT",  "Message Type",             "STRING",        "01=Order,02=Expedite,03=Defer,04=Cancel"),
        JDEField("UORG",  "Quantity",                 "MATH_NUMERIC", "Quantity suggested by MRP"),
        JDEField("DRQJ",  "Required Date",            "JDEDATE",       "Date supply is needed"),
        JDEField("STRT",  "Suggested Start Date",     "JDEDATE",       "Suggested order start date"),
        JDEField("DOCO",  "Related WO/PO",            "MATH_NUMERIC", "Existing order being modified"),
        JDEField("DCTO",  "Document Type",            "STRING",        "Type of related order"),
        JDEField("PRIO",  "Priority",                 "STRING",        "Planning priority"),
        JDEField("PROC",  "Processed Flag",           "STRING",        "Y=Message has been processed"),
    ]
)

F3413 = JDETable(
    name="F3413",
    description="MRP Lower Level Requirements — pegged demand showing where requirements originate",
    module="MRP / Planning",
    key_fields=["ITM", "MMCU", "TRDJ", "LNID"],
    related_tables=["F3411", "F4101"],
    fields=[
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Component item being planned"),
        JDEField("MMCU",  "Branch/Plant",             "STRING",        "Planning plant"),
        JDEField("TRDJ",  "Date",                     "JDEDATE",       "Requirement date"),
        JDEField("LNID",  "Line Number",              "MATH_NUMERIC", "Sequence number"),
        JDEField("RQTY",  "Required Quantity",        "MATH_NUMERIC", "Quantity required"),
        JDEField("AQTY",  "Available Quantity",       "MATH_NUMERIC", "Quantity available on that date"),
        JDEField("PKIT",  "Parent Item",              "MATH_NUMERIC", "Parent item driving this requirement"),
        JDEField("PDOC",  "Parent Document",          "MATH_NUMERIC", "Parent WO or SO number"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# ITEM MASTER (used across all manufacturing)
# ─────────────────────────────────────────────────────────────────────────────

F4101 = JDETable(
    name="F4101",
    description="Item Master — defines all items including manufactured, purchased, and phantoms",
    module="Inventory / Manufacturing",
    key_fields=["ITM"],
    related_tables=["F4102", "F3002", "F3003", "F41021"],
    fields=[
        JDEField("ITM",   "Item Number (short)",      "MATH_NUMERIC", "Short item number (system-assigned)"),
        JDEField("LITM",  "Item Number (2nd)",        "STRING",        "Customer or user-defined item number"),
        JDEField("AITM",  "Item Number (3rd)",        "STRING",        "Supplier or alternate item number"),
        JDEField("DSC1",  "Description 1",            "STRING",        "Primary item description"),
        JDEField("DSC2",  "Description 2",            "STRING",        "Secondary item description"),
        JDEField("STKT",  "Stocking Type",            "STRING",        "C=Manufactured,P=Purchased,O=Phantom,K=Kit"),
        JDEField("STVT",  "Storage Type",             "STRING",        "How item is stored"),
        JDEField("UOM",   "Primary UOM",              "STRING",        "Primary unit of measure"),
        JDEField("UOM1",  "Weight UOM",               "STRING",        "Unit of measure for weight"),
        JDEField("UOM2",  "Volume UOM",               "STRING",        "Unit of measure for volume"),
        JDEField("PRPO",  "Planner Buyer",            "STRING",        "Planner/buyer code"),
        JDEField("BREV",  "BOM Revision Level",       "STRING",        "Current BOM revision level"),
        JDEField("RREV",  "Routing Revision Level",   "STRING",        "Current routing revision level"),
        JDEField("LDTE",  "Lead Time Days",           "MATH_NUMERIC", "Manufacturing or purchasing lead time"),
        JDEField("SLTP",  "Sales/Inventory Item",     "STRING",        "Y=Stocked item"),
        JDEField("MMCU",  "Primary Branch/Plant",     "STRING",        "Default manufacturing plant"),
        JDEField("GLPT",  "GL Class",                 "STRING",        "GL account class code"),
        JDEField("CDCD",  "Commodity Code",           "STRING",        "Commodity classification"),
        JDEField("CWUN",  "Unit Weight",              "MATH_NUMERIC", "Weight per unit"),
        JDEField("CVOL",  "Unit Volume",              "MATH_NUMERIC", "Volume per unit"),
    ]
)

F4102 = JDETable(
    name="F4102",
    description="Item Branch/Plant — item settings specific to each branch/plant",
    module="Inventory / Manufacturing",
    key_fields=["ITM", "MCU"],
    related_tables=["F4101", "F41021", "F3002"],
    fields=[
        JDEField("ITM",   "Item Number (short)",      "MATH_NUMERIC", "Short item number"),
        JDEField("MCU",   "Branch/Plant",             "STRING",        "Branch or plant"),
        JDEField("LOCN",  "Primary Location",         "STRING",        "Default warehouse location"),
        JDEField("LOTN",  "Lot/Serial Flag",          "STRING",        "Lot/serial number control"),
        JDEField("PLNF",  "Planning Fence",           "MATH_NUMERIC", "Days in planning fence"),
        JDEField("TRFL",  "Transfer Lead Time",       "MATH_NUMERIC", "Lead time for inter-plant transfers"),
        JDEField("LDTE",  "Lead Time Level",          "MATH_NUMERIC", "Level lead time in days"),
        JDEField("PRPO",  "Planner",                  "STRING",        "Planner assigned to item at plant"),
        JDEField("BUYR",  "Buyer",                    "STRING",        "Buyer assigned to item at plant"),
        JDEField("RPOL",  "Reorder Policy",           "STRING",        "M=MRP,R=Reorder Point,MFG=Manufacturing"),
        JDEField("SSQT",  "Safety Stock",             "MATH_NUMERIC", "Safety stock quantity"),
        JDEField("MINQ",  "Minimum Order Qty",        "MATH_NUMERIC", "Minimum order quantity"),
        JDEField("MXTH",  "Maximum Order Qty",        "MATH_NUMERIC", "Maximum order quantity"),
        JDEField("MULT",  "Order Multiple",           "MATH_NUMERIC", "Order must be multiple of this qty"),
        JDEField("BACK",  "Backorders Allowed",       "STRING",        "Y=Allow backorders"),
        JDEField("PQOH",  "On Hand Quantity",         "MATH_NUMERIC", "Current on-hand quantity"),
        JDEField("PRQT",  "On PO Quantity",           "MATH_NUMERIC", "Quantity on purchase orders"),
        JDEField("PREQ",  "On WO Quantity",           "MATH_NUMERIC", "Quantity on work orders"),
        JDEField("SOQS",  "On SO Quantity",           "MATH_NUMERIC", "Quantity committed to sales orders"),
    ]
)

F41021 = JDETable(
    name="F41021",
    description="Item Location File — inventory balances by lot and location",
    module="Inventory",
    key_fields=["ITM", "MCU", "LOCN", "LOTN"],
    related_tables=["F4102", "F4101"],
    fields=[
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Short item number"),
        JDEField("MCU",   "Branch/Plant",             "STRING",        "Branch or plant"),
        JDEField("LOCN",  "Location",                 "STRING",        "Warehouse location"),
        JDEField("LOTN",  "Lot/Serial Number",        "STRING",        "Lot or serial number"),
        JDEField("PQOH",  "On Hand Qty",              "MATH_NUMERIC", "Physical on-hand quantity"),
        JDEField("PREQ",  "Committed Qty",            "MATH_NUMERIC", "Quantity committed to orders"),
        JDEField("PQOA",  "Available Qty",            "MATH_NUMERIC", "Available = On Hand - Committed"),
        JDEField("LEXP",  "Lot Expiry Date",          "JDEDATE",       "Lot expiration date"),
        JDEField("LFMN",  "Lot From Date",            "JDEDATE",       "Date lot was created"),
        JDEField("LOTS",  "Lot Status",               "STRING",        "Lot quality/hold status"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT COSTING (Module 30)
# ─────────────────────────────────────────────────────────────────────────────

F30026 = JDETable(
    name="F30026",
    description="Frozen Cost Components — frozen standard cost detail by item and cost method",
    module="Product Costing",
    key_fields=["ITM", "MCU", "CMTH", "CDCD"],
    related_tables=["F4101", "F4105"],
    fields=[
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Short item number"),
        JDEField("MCU",   "Branch/Plant",             "STRING",        "Plant"),
        JDEField("CMTH",  "Cost Method",              "STRING",        "07=Standard,01=Weighted Avg,02=FIFO"),
        JDEField("CDCD",  "Cost Component",           "STRING",        "B1=Purchased,C1=Labor,C2=Machine,D1=Overhead"),
        JDEField("CUNI",  "Unit Cost",                "MATH_NUMERIC", "Unit cost for this component"),
        JDEField("TCOS",  "Total Cost",               "MATH_NUMERIC", "Extended total cost"),
        JDEField("UPMJ",  "Last Updated",             "JDEDATE",       "Date cost was last updated"),
    ]
)

F4105 = JDETable(
    name="F4105",
    description="Item Cost File — standard/average costs by item, plant and cost method",
    module="Product Costing",
    key_fields=["ITM", "MCU", "CMTH"],
    related_tables=["F4101", "F30026"],
    fields=[
        JDEField("ITM",   "Item Number",              "MATH_NUMERIC", "Short item number"),
        JDEField("MCU",   "Branch/Plant",             "STRING",        "Plant"),
        JDEField("CMTH",  "Cost Method",              "STRING",        "07=Standard,01=Weighted Avg,02=FIFO"),
        JDEField("UNCS",  "Unit Cost",                "MATH_NUMERIC", "Current unit cost"),
        JDEField("UPMJ",  "Last Updated",             "JDEDATE",       "Date cost was last updated"),
        JDEField("LUPD",  "Last Updated By",          "STRING",        "User who last updated cost"),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY — all tables indexed by name
# ─────────────────────────────────────────────────────────────────────────────

ALL_TABLES: Dict[str, JDETable] = {
    t.name: t for t in [
        F4801, F4801T, F4802,
        F3002, F3003, F3006,
        F3111, F3112, F3116,
        F3411, F3413,
        F4101, F4102, F41021,
        F30026, F4105,
    ]
}

MODULE_GROUPS = {
    "Work Orders":        ["F4801", "F4801T", "F4802"],
    "Bill of Materials":  ["F3002"],
    "Routings":           ["F3003", "F3006"],
    "Shop Floor":         ["F3111", "F3112", "F3116"],
    "MRP / Planning":     ["F3411", "F3413"],
    "Inventory":          ["F4101", "F4102", "F41021"],
    "Product Costing":    ["F30026", "F4105"],
}

# Work Order Status codes
WO_STATUS_CODES = {
    "10": "Entered", "20": "Approved", "25": "Parts Committed",
    "30": "Released", "35": "Parts Issued", "40": "In Process",
    "60": "Parts Received", "90": "Complete", "95": "In Variance",
    "99": "Closed",
}

# Document Types for manufacturing
MFG_DOC_TYPES = {
    "WO": "Work Order", "WR": "Rework Order", "WM": "Maintenance Work Order",
    "WT": "Teardown Order", "WC": "Co-product Work Order",
}

def get_table_summary() -> str:
    """Return a compact summary of all manufacturing tables for the LLM system prompt."""
    lines = []
    for module, tables in MODULE_GROUPS.items():
        lines.append(f"\n### {module}")
        for tname in tables:
            t = ALL_TABLES[tname]
            key_str = ", ".join(t.key_fields)
            lines.append(f"  {tname}: {t.description} [keys: {key_str}]")
    return "\n".join(lines)


def get_field_info(table_name: str) -> Optional[str]:
    """Return field reference for a specific table."""
    t = ALL_TABLES.get(table_name.upper())
    if not t:
        return None
    lines = [f"**{t.name}** — {t.description}", f"Module: {t.module}", ""]
    lines.append(f"{'Alias':<8} {'Name':<28} {'Type':<14} Description")
    lines.append("-" * 80)
    for f in t.fields:
        lines.append(f"{f.alias:<8} {f.name:<28} {f.data_type:<14} {f.description}")
    if t.related_tables:
        lines.append(f"\nRelated tables: {', '.join(t.related_tables)}")
    return "\n".join(lines)
