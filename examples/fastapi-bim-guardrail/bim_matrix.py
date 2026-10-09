# SPDX-FileCopyrightText: 2026 Jose Manuel Caamaño González (jmcaamanog)
# SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)
#
# SPDX-License-Identifier: Apache-2.0

"""BIM Work Breakdown Structure (WBS) Matrix for International Retail Store Roll-Outs.

Defines the segregation between Management Packages (Contracting & Tenders)
and BIM Disciplines (Technical Modeling and Cross-Disciplinary Coordination).
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ManagementPackage:
    """Management / Contracting Work Package."""

    code: str
    name_es: str
    name_en: str


@dataclass(frozen=True)
class BimDiscipline:
    """BIM Technical Modeling Discipline."""

    code: str
    name_es: str
    name_en: str


@dataclass(frozen=True)
class BimMatrixEntry:
    """Mapping between Management Package and BIM Discipline."""

    package_code: str
    package_name_es: str
    package_name_en: str
    discipline_code: str
    discipline_name_es: str
    discipline_name_en: str


BIM_WBS_MATRIX: Final[tuple[BimMatrixEntry, ...]] = (
    BimMatrixEntry("000GRL", "GESTIÓN PROYECTO", "PROJECT MANAGEMENT", "000", "GESTIÓN", "MANAGEMENT"),
    BimMatrixEntry("000GRL", "GESTIÓN OBRA", "CONSTRUCTION MANAGEMENT", "000", "GESTIÓN", "MANAGEMENT"),
    BimMatrixEntry("000GRL", "GESTIÓN PROYECTO", "PROJECT MANAGEMENT", "CRD", "COORDINACIÓN", "COORDINATION"),
    BimMatrixEntry("010EXI", "ESTADO ACTUAL", "EXISTING CONDITIONS", "ARQ", "ARQUITECTURA", "ARCHITECTURE"),
    BimMatrixEntry("020CON", "CONSULTING", "CONSULTANCY", "ARQ", "ARQUITECTURA", "ARCHITECTURE"),
    BimMatrixEntry("100OBR", "OBRA IN SITU", "IN SITU CONSTRUCTION", "OBR", "OBRA IN SITU", "IN SITU CONSTRUCTION"),
    BimMatrixEntry("110CAM", "CARPINTERÍA METÁLICA", "METALWORK", "FAC", "FACHADA", "FACADE"),
    BimMatrixEntry("120PAU", "PUERTAS AUTOMÁTICAS", "AUTOMATIC DOORS", "FAC", "FACHADA", "FACADE"),
    BimMatrixEntry("130ENV", "ENVOLVENTE", "ENVELOPE", "ENV", "ENVOLVENTE", "ENVELOPE"),
    BimMatrixEntry(
        "150MOA", "MOBILIARIO ALMACENES", "STOCKROOM FURNITURE", "MOA", "MOBILIARIO ALMACENES", "STOCKROOM FURNITURE"
    ),
    BimMatrixEntry("170CMD", "CARPINTERÍA MADERA", "WOOD JOINERY", "CMD", "CARPINTERÍA MADERA", "WOOD JOINERY"),
    BimMatrixEntry("200CLI", "CLIMATIZACIÓN", "AIR CONDITION", "CLI", "CLIMATIZACIÓN", "AIR CONDITION"),
    BimMatrixEntry("200CLI", "CLIMATIZACIÓN", "AIR CONDITION", "HUM", "CONTROL DE HUMOS", "SMOKE CONTROL"),
    BimMatrixEntry("300PCI", "INSTAL. PCI", "FIRE ENGINEERING", "HUM", "CONTROL DE HUMOS", "SMOKE CONTROL"),
    BimMatrixEntry("110CAM", "CARPINTERÍA METÁLICA", "METALWORK", "HUM", "CONTROL DE HUMOS", "SMOKE CONTROL"),
    BimMatrixEntry("130ENV", "ENVOLVENTE", "ENVELOPE", "HUM", "CONTROL DE HUMOS", "SMOKE CONTROL"),
    BimMatrixEntry("300PCI", "INSTAL. PCI", "FIRE ENGINEERING", "PCI", "INSTAL. PCI", "FIRE ENGINEERING"),
    BimMatrixEntry(
        "400FNT",
        "FONTANERÍA Y SANEAMIENTO",
        "PLUMBING AND DRAINAGE",
        "FNT",
        "FONTANERÍA Y SANEAMIENTO",
        "PLUMBING AND DRAINAGE",
    ),
    BimMatrixEntry("500ELE", "ELECTRICIDAD", "ELECTRICITY", "ELE", "ELECTRICIDAD", "ELECTRICITY"),
    BimMatrixEntry(
        "510IL1",
        "ILUMINACIÓN APARATOS IMAGEN",
        "SALES AREA LIGHTING",
        "ALU",
        "ILUMINACIÓN APARATOS IMAGEN",
        "SALES AREA LIGHTING",
    ),
    BimMatrixEntry("510IL2", "ILUMINACIÓN LINEAL", "LINEAR LIGHTING", "ALU", "ILUMINACIÓN LINEAL", "LINEAR LIGHTING"),
    BimMatrixEntry(
        "540RED",
        "INFRAESTRUCTURAS DE RED",
        "NETWORK INFRASTRUCTURE",
        "RED",
        "INFRAESTRUCTURAS DE RED",
        "NETWORK INFRASTRUCTURE",
    ),
    BimMatrixEntry("600ATH", "ANTENAS ANTIHURTO", "ANTITHEFT ANTENNA", "ATH", "ANTENAS ANTIHURTO", "ANTITHEFT ANTENNA"),
    BimMatrixEntry("610CTV", "CCTV", "CCTV", "CTV", "CCTV", "CCTV"),
    BimMatrixEntry("620SON", "SONIDO", "SOUND", "SON", "SONIDO", "SOUND"),
    BimMatrixEntry("630VIS", "VISUALES", "VISUALS", "VIS", "VISUALES", "VISUALS"),
    BimMatrixEntry(
        "700EYA",
        "ESCALERAS Y ASCENSORES",
        "STAIRS AND ELEVATORS",
        "EYA",
        "ESCALERAS Y ASCENSORES",
        "STAIRS AND ELEVATORS",
    ),
    BimMatrixEntry("900MET", "ESTRUCTURA METÁLICA", "METALLIC STRUCTURE", "EST", "ESTRUCTURA", "STRUCTURE"),
    BimMatrixEntry("000GRL", "GEOMETRÍA ESTRUCTURA", "STRUCTURE GEOMETRY", "EST", "ESTRUCTURA", "STRUCTURE"),
)


def get_matrix_entries_by_package(package_code: str) -> list[BimMatrixEntry]:
    """Retrieve all BIM discipline mappings for a management package."""
    return [entry for entry in BIM_WBS_MATRIX if entry.package_code.upper() == package_code.upper()]


def get_matrix_entries_by_discipline(discipline_code: str) -> list[BimMatrixEntry]:
    """Retrieve all management package mappings for a BIM discipline."""
    return [entry for entry in BIM_WBS_MATRIX if entry.discipline_code.upper() == discipline_code.upper()]
