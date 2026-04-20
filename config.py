SUBREDDITS = [
    "Asthma",
    "EGPA",
    "ChronicIllness",
    "AskDocs",
    "eosinophilic",
    "Allergies",
    "Autoimmune",
    "severeasthma",
    "biologics",
    "Nucala",
    "respiratory",
    "LungDisease",
]

SEARCH_KEYWORDS = [
    # Drug names — most targeted
    "mepolizumab", "nucala",
    # Disease
    "severe asthma", "eosinophilic asthma", "EGPA",
    # Treatment
    "asthma biologic", "asthma inhaler", "asthma treatment",
    # Patient journey
    "asthma diagnosis", "asthma exacerbation",
    # Access/cost
    "insurance asthma", "asthma cost",
    # Biosimilar/biologic perception
    "biosimilar asthma", "biologic injection",
    # QoL
    "asthma quality of life",
]

STAKEHOLDER_KEYWORDS = {
    "Patients": [
        "i have asthma", "my asthma", "i was diagnosed", "my inhaler",
        "i take nucala", "i started biologic", "my breathing", "i feel",
        "my doctor prescribed", "i can't breathe", "my symptoms",
    ],
    "Physicians": [
        "as a doctor", "as a physician", "my patients", "i prescribe",
        "clinical practice", "i recommend", "in my experience as",
        "pulmonologist here", "allergist here", "i treat",
    ],
    "Pharmacists": [
        "as a pharmacist", "at the pharmacy", "dispensing", "prescription fill",
        "pharmacist here", "i dispense",
    ],
    "Caregivers": [
        "my child has asthma", "my son", "my daughter", "caring for",
        "my husband asthma", "my wife asthma", "my parent asthma",
        "i care for", "caregiver",
    ],
    "Payers": [
        "insurance denied", "prior auth", "insurance coverage", "formulary",
        "insurance company", "my plan", "copay", "deductible",
    ],
}

DRUG_NAMES = [
    "mepolizumab", "nucala", "dupilumab", "dupixent",
    "benralizumab", "fasenra", "tezepelumab", "tezspire",
    "omalizumab", "xolair", "reslizumab", "cinqair",
    "tralokinumab", "adbry",
]

OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SCRAPE_LIMIT = 5    # posts per keyword search — fast run, saves incrementally
CHUNK_SIZE = 900    # words per chunk — larger context for better RAG reasoning
CHUNK_OVERLAP = 100
