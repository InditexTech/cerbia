# SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from cerbia.core.scanners.tender import TenderDataScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


def test_tender_data_scanner_empty_text() -> None:
    scanner = TenderDataScanner()
    result = scanner.scan("")

    assert result.risk_score == 0.0
    assert result.rationale == "No text provided"
    assert result.matches == []


def test_tender_data_scanner_safe_text() -> None:
    scanner = TenderDataScanner()
    safe_text = (
        "The retail flagship store features energy-efficient HVAC units and natural oak flooring. "
        "All materials adhere to European sustainability standards."
    )
    result = scanner.scan(safe_text)

    assert result.risk_score == 0.0
    assert result.rationale == "No confidential tender data detected"
    assert result.matches == []


def test_tender_data_scanner_detects_bc3_records() -> None:
    scanner = TenderDataScanner()
    bc3_snippet = (
        "Project tender specifications:\n"
        "~V|FIEBDC-3/2020|Base de Costes Inditex 2026|\n"
        "~K|13.00\\6.00|\n"
        "~C|UAA010\\m2\\42.50|Solera de hormigón armado de 15 cm...|\n"
        "~D|UAA010\\MAT01\\1.00\\MTR02\\0.50|\n"
        "~M|UAA010\\Planta Baja ZARA\\1\\25.0\\10.0\\250.0|\n"
        "End of specifications."
    )
    result = scanner.scan(bc3_snippet)

    assert result.risk_score >= 0.90
    assert "BC3 Record" in result.rationale
    assert len(result.matches) == 5

    # Verify that match spans extract exact BC3 line markers
    first_match = result.matches[0]
    extracted = bc3_snippet[first_match.start : first_match.end]
    assert extracted.startswith("~V|FIEBDC-3/2020|")


def test_tender_data_scanner_detects_pem_and_budgets() -> None:
    scanner = TenderDataScanner()
    text = (
        "Desglose presupuestario confidencial: "
        "El PEM: 1.250.000 € y el Presupuesto Base de Licitación: 1.850.000,50 EUR "
        "con un B.I.: 6% y Gastos Generales: 13%."
    )
    result = scanner.scan(text)

    assert result.risk_score >= 0.80
    assert "Tender Budget" in result.rationale
    assert len(result.matches) == 4

    matched_texts = [text[m.start : m.end] for m in result.matches]
    assert any("PEM: 1.250.000 €" in s for s in matched_texts)
    assert any("Presupuesto Base de Licitación: 1.850.000,50 EUR" in s for s in matched_texts)


def test_tender_data_scanner_detects_decimal_coordinates() -> None:
    scanner = TenderDataScanner()
    text = "Nueva localización de tienda confidencial en (43.362345, -8.411234)."
    result = scanner.scan(text)

    assert result.risk_score >= 0.75
    assert "Coordinates (Decimal)" in result.rationale
    assert len(result.matches) == 1
    assert text[result.matches[0].start : result.matches[0].end] == "43.362345, -8.411234"


def test_tender_data_scanner_detects_dms_coordinates() -> None:
    scanner = TenderDataScanner()
    text = "Coordenadas del centro logístico: 43°21'44.4\"N 8°24'40.4\"W de alta resolución."
    result = scanner.scan(text)

    assert result.risk_score >= 0.75
    assert "Coordinates (DMS)" in result.rationale
    assert len(result.matches) == 1
    assert "43°21'44.4\"N 8°24'40.4\"W" in text[result.matches[0].start : result.matches[0].end]


def test_tender_data_scanner_detects_utm_coordinates() -> None:
    scanner = TenderDataScanner()
    text = "Localización de parcela en UTM Zone 29N X: 547890 Y: 4799120."
    result = scanner.scan(text)

    assert result.risk_score >= 0.75
    assert "Coordinates (UTM)" in result.rationale
    assert len(result.matches) == 1
    assert "UTM Zone 29N X: 547890 Y: 4799120" in text[result.matches[0].start : result.matches[0].end]


def test_tender_data_scanner_detects_tender_dockets() -> None:
    scanner = TenderDataScanner()
    text = (
        "Expedientes de licitación: EXP-2026/00142-OBR y LIC-2026/ESP-0081 "
        "con anuncio en Diario Oficial 2026/S 123-456789."
    )
    result = scanner.scan(text)

    assert result.risk_score >= 0.70
    assert "Tender Docket" in result.rationale
    assert len(result.matches) == 3

    matched_texts = [text[m.start : m.end] for m in result.matches]
    assert "EXP-2026/00142-OBR" in matched_texts
    assert "LIC-2026/ESP-0081" in matched_texts
    assert "2026/S 123-456789" in matched_texts


def test_tender_data_scanner_toggle_detectors() -> None:
    # Disable BC3 and Coordinates, enable only budgets and dockets
    scanner = TenderDataScanner(detect_bc3=False, detect_coordinates=False)
    text = "~C|UAA010\\m2\\42.50|Solera|\nCoordenadas: 43.362345, -8.411234\nPEM: 1.250.000 €\nEXP-2026/00142-OBR"
    result = scanner.scan(text)

    assert len(result.matches) == 2
    matched_texts = [text[m.start : m.end] for m in result.matches]
    assert "PEM: 1.250.000 €" in matched_texts
    assert "EXP-2026/00142-OBR" in matched_texts
    assert not any("~C" in s for s in matched_texts)
    assert not any("43.362345" in s for s in matched_texts)


def test_tender_data_scanner_custom_action_and_severity() -> None:
    scanner = TenderDataScanner(severity=Severity.CRITICAL, action=Action.WARN)

    assert scanner.scanner_id == "tender_data"
    assert scanner.scanner_name == "Tender Data"
    assert scanner.severity == Severity.CRITICAL
    assert scanner.action == Action.WARN
    assert scanner.content_types == (ContentType.TEXT,)


def test_tender_data_scanner_matches_sorted_by_start_offset() -> None:
    scanner = TenderDataScanner()
    text = "Ref EXP-2026/00142-OBR asociada a ubicación 43.362345, -8.411234 con un PEM: 500.000 €."
    result = scanner.scan(text)

    assert len(result.matches) == 3
    # Check monotonic ascending order of start positions
    starts = [m.start for m in result.matches]
    assert starts == sorted(starts)
