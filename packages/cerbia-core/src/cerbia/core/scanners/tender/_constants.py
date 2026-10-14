# SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)
#
# SPDX-License-Identifier: Apache-2.0

"""Constants and regex patterns for technical tender data detection."""

import re

# 1. FIEBDC-3 / BC3 Standard Architectural Bidding Exchange Lines
# Matches record markers (~V, ~K, ~C, ~D, ~M, ~T) at the beginning of a line or text
BC3_RECORD_PATTERN = re.compile(
    r"(?:^|[\r\n])\s*(~[VKCDMT]\s*[|\\][^\r\n]*)",
    re.MULTILINE,
)

# 2. PEM, PBL, Contractor Overheads, and Tender Financial Figures
TENDER_BUDGET_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"(?:PEM|Presupuesto\s+de\s+Ejecuci[oó]n\s+Material)\s*(?:[:=]|de)?\s*(?:\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,]\d{1,2})?\s*(?:€|\bEUR\b|\beuros?\b)"
    r"|(?:PBL|Presupuesto\s+Base\s+de\s+Licitaci[oó]n)\s*(?:[:=]|de)?\s*(?:\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,]\d{1,2})?\s*(?:€|\bEUR\b|\beuros?\b)"
    r"|(?:Presupuesto\s+de\s+(?:Adjudicaci[oó]n|Contrata))\s*(?:[:=]|de)?\s*(?:\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,]\d{1,2})?\s*(?:€|\bEUR\b|\beuros?\b)"
    r"|(?:B\.?I\.?|Beneficio\s+Industrial|G\.?G\.?|Gastos\s+Generales)\s*[:=]?\s*\d+(?:[.,]\d+)?\s*%"
    r")"
)

# 3. Official Public/Private Technical Tender Dockets
TENDER_DOCKET_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"(?:EXP|EXPEDIENTE)[-_/](?:\d{4}[-_/][A-Z0-9_-]+|[A-Z0-9]{2,8}[-_/]\d{2,6}[-_/][A-Z0-9_-]+)"
    r"|(?:LIC|LICITACI[OÓ]N)[-_/][A-Z0-9_/-]{4,25}"
    r"|\d{4}/S\s+\d{3}-\d{6,8}"
    r")\b"
)

# 4. High-Precision Geographic Coordinates (Sub-meter commercial plot locations)
COORDINATE_DECIMAL_PATTERN = re.compile(
    r"(?<![0-9])([-+]?(?:[1-8]?\d(?:\.\d{4,})|90(?:\.0{4,})))\s*,\s*([-+]?(?:180(?:\.0{4,})|(?:1[0-7]\d|\d{1,2})(?:\.\d{4,})))(?![0-9])"
)

COORDINATE_DMS_PATTERN = re.compile(
    r"\b([0-8]?\d|90)[°º]\s*([0-5]?\d)['′]\s*([0-5]?\d(?:\.\d+)?)[\"″]?\s*([NSns])\s*[,;]?\s*(?:180|1[0-7]\d|\d{1,3})[°º]\s*([0-5]?\d)['′]\s*([0-5]?\d(?:\.\d+)?)[\"″]?\s*([EWOWewow])\b"
)

COORDINATE_UTM_PATTERN = re.compile(
    r"(?i)\b(?:UTM|ETRS89|WGS84)\s+(?:Zone\s+)?(\d{1,2}[A-Z])\s+(?:X\s*[:=]?\s*(\d{6,7}(?:\.\d+)?)\s+Y\s*[:=]?\s*(\d{7}(?:\.\d+)?)|(\d{6,7}(?:\.\d+)?)\s+(\d{7}(?:\.\d+)?))\b"
)

# Risk scoring constants
SCORE_BC3 = 0.90
SCORE_BUDGET = 0.80
SCORE_COORDINATES = 0.75
SCORE_DOCKET = 0.70
