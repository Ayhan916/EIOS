"""
NACE Rev. 2 — 2-digit code to section mapping.

Covers all 88 NACE 2-digit divisions used in EU statistical classification.
Source: Eurostat NACE Rev. 2 (2008), https://ec.europa.eu/eurostat/ramon/
"""

from __future__ import annotations

# Maps 2-digit NACE code → (letter section, human-readable section name)
NACE_2DIGIT: dict[str, tuple[str, str]] = {
    # Section A — Agriculture, Forestry and Fishing
    "01": ("A", "Agriculture, Forestry and Fishing"),
    "02": ("A", "Agriculture, Forestry and Fishing"),
    "03": ("A", "Agriculture, Forestry and Fishing"),
    # Section B — Mining and Quarrying
    "05": ("B", "Mining and Quarrying"),
    "06": ("B", "Mining and Quarrying"),
    "07": ("B", "Mining and Quarrying"),
    "08": ("B", "Mining and Quarrying"),
    "09": ("B", "Mining and Quarrying"),
    # Section C — Manufacturing
    "10": ("C", "Manufacturing"),
    "11": ("C", "Manufacturing"),
    "12": ("C", "Manufacturing"),
    "13": ("C", "Manufacturing"),
    "14": ("C", "Manufacturing"),
    "15": ("C", "Manufacturing"),
    "16": ("C", "Manufacturing"),
    "17": ("C", "Manufacturing"),
    "18": ("C", "Manufacturing"),
    "19": ("C", "Manufacturing"),
    "20": ("C", "Manufacturing"),
    "21": ("C", "Manufacturing"),
    "22": ("C", "Manufacturing"),
    "23": ("C", "Manufacturing"),
    "24": ("C", "Manufacturing"),
    "25": ("C", "Manufacturing"),
    "26": ("C", "Manufacturing"),
    "27": ("C", "Manufacturing"),
    "28": ("C", "Manufacturing"),
    "29": ("C", "Manufacturing"),
    "30": ("C", "Manufacturing"),
    "31": ("C", "Manufacturing"),
    "32": ("C", "Manufacturing"),
    "33": ("C", "Manufacturing"),
    # Section D — Electricity, Gas, Steam and Air Conditioning Supply
    "35": ("D", "Electricity, Gas, Steam and Air Conditioning Supply"),
    # Section E — Water Supply; Sewerage, Waste Management
    "36": ("E", "Water Supply; Sewerage, Waste Management"),
    "37": ("E", "Water Supply; Sewerage, Waste Management"),
    "38": ("E", "Water Supply; Sewerage, Waste Management"),
    "39": ("E", "Water Supply; Sewerage, Waste Management"),
    # Section F — Construction
    "41": ("F", "Construction"),
    "42": ("F", "Construction"),
    "43": ("F", "Construction"),
    # Section G — Wholesale and Retail Trade
    "45": ("G", "Wholesale and Retail Trade"),
    "46": ("G", "Wholesale and Retail Trade"),
    "47": ("G", "Wholesale and Retail Trade"),
    # Section H — Transportation and Storage
    "49": ("H", "Transportation and Storage"),
    "50": ("H", "Transportation and Storage"),
    "51": ("H", "Transportation and Storage"),
    "52": ("H", "Transportation and Storage"),
    "53": ("H", "Transportation and Storage"),
    # Section I — Accommodation and Food Service
    "55": ("I", "Accommodation and Food Service Activities"),
    "56": ("I", "Accommodation and Food Service Activities"),
    # Section J — Information and Communication
    "58": ("J", "Information and Communication"),
    "59": ("J", "Information and Communication"),
    "60": ("J", "Information and Communication"),
    "61": ("J", "Information and Communication"),
    "62": ("J", "Information and Communication"),
    "63": ("J", "Information and Communication"),
    # Section K — Financial and Insurance Activities
    "64": ("K", "Financial and Insurance Activities"),
    "65": ("K", "Financial and Insurance Activities"),
    "66": ("K", "Financial and Insurance Activities"),
    # Section L — Real Estate Activities
    "68": ("L", "Real Estate Activities"),
    # Section M — Professional, Scientific and Technical Activities
    "69": ("M", "Professional, Scientific and Technical Activities"),
    "70": ("M", "Professional, Scientific and Technical Activities"),
    "71": ("M", "Professional, Scientific and Technical Activities"),
    "72": ("M", "Professional, Scientific and Technical Activities"),
    "73": ("M", "Professional, Scientific and Technical Activities"),
    "74": ("M", "Professional, Scientific and Technical Activities"),
    "75": ("M", "Professional, Scientific and Technical Activities"),
    # Section N — Administrative and Support Service Activities
    "77": ("N", "Administrative and Support Service Activities"),
    "78": ("N", "Administrative and Support Service Activities"),
    "79": ("N", "Administrative and Support Service Activities"),
    "80": ("N", "Administrative and Support Service Activities"),
    "81": ("N", "Administrative and Support Service Activities"),
    "82": ("N", "Administrative and Support Service Activities"),
    # Section O — Public Administration and Defence
    "84": ("O", "Public Administration and Defence"),
    # Section P — Education
    "85": ("P", "Education"),
    # Section Q — Human Health and Social Work
    "86": ("Q", "Human Health and Social Work Activities"),
    "87": ("Q", "Human Health and Social Work Activities"),
    "88": ("Q", "Human Health and Social Work Activities"),
    # Section R — Arts, Entertainment and Recreation
    "90": ("R", "Arts, Entertainment and Recreation"),
    "91": ("R", "Arts, Entertainment and Recreation"),
    "92": ("R", "Arts, Entertainment and Recreation"),
    "93": ("R", "Arts, Entertainment and Recreation"),
    # Section S — Other Service Activities
    "94": ("S", "Other Service Activities"),
    "95": ("S", "Other Service Activities"),
    "96": ("S", "Other Service Activities"),
    # Section T — Households as Employers
    "97": ("T", "Activities of Households as Employers"),
    "98": ("T", "Activities of Households as Employers"),
    # Section U — Extraterritorial Organisations
    "99": ("U", "Activities of Extraterritorial Organisations"),
}

# Human-readable division names for key Catena-X relevant sectors
NACE_DIVISION_NAMES: dict[str, str] = {
    "01": "Crop and animal production, hunting",
    "02": "Forestry and logging",
    "03": "Fishing and aquaculture",
    "05": "Mining of coal and lignite",
    "06": "Extraction of crude petroleum and natural gas",
    "07": "Mining of metal ores",
    "08": "Other mining and quarrying",
    "09": "Mining support service activities",
    "10": "Manufacture of food products",
    "11": "Manufacture of beverages",
    "12": "Manufacture of tobacco products",
    "13": "Manufacture of textiles",
    "14": "Manufacture of wearing apparel",
    "15": "Manufacture of leather and related products",
    "16": "Manufacture of wood and wood products",
    "17": "Manufacture of paper and paper products",
    "18": "Printing and reproduction of recorded media",
    "19": "Manufacture of coke and refined petroleum products",
    "20": "Manufacture of chemicals and chemical products",
    "21": "Manufacture of basic pharmaceutical products",
    "22": "Manufacture of rubber and plastic products",
    "23": "Manufacture of other non-metallic mineral products",
    "24": "Manufacture of basic metals",
    "25": "Manufacture of fabricated metal products",
    "26": "Manufacture of computer, electronic and optical products",
    "27": "Manufacture of electrical equipment",
    "28": "Manufacture of machinery and equipment",
    "29": "Manufacture of motor vehicles, trailers and semi-trailers",
    "30": "Manufacture of other transport equipment",
    "31": "Manufacture of furniture",
    "32": "Other manufacturing",
    "33": "Repair and installation of machinery and equipment",
    "35": "Electricity, gas, steam and air conditioning supply",
    "36": "Water collection, treatment and supply",
    "37": "Sewerage",
    "38": "Waste collection, treatment and disposal",
    "39": "Remediation activities",
    "41": "Construction of buildings",
    "42": "Civil engineering",
    "43": "Specialised construction activities",
    "45": "Wholesale and retail trade and repair of motor vehicles",
    "46": "Wholesale trade",
    "47": "Retail trade",
    "49": "Land transport and transport via pipelines",
    "50": "Water transport",
    "51": "Air transport",
    "52": "Warehousing and support activities for transportation",
    "53": "Postal and courier activities",
    "55": "Accommodation",
    "56": "Food and beverage service activities",
    "58": "Publishing activities",
    "59": "Motion picture, video and television programme production",
    "60": "Programming and broadcasting activities",
    "61": "Telecommunications",
    "62": "Computer programming, consultancy and related activities",
    "63": "Information service activities",
    "64": "Financial service activities",
    "65": "Insurance, reinsurance and pension funding",
    "66": "Activities auxiliary to financial services",
    "68": "Real estate activities",
    "69": "Legal and accounting activities",
    "70": "Activities of head offices; management consultancy",
    "71": "Architectural and engineering activities",
    "72": "Scientific research and development",
    "73": "Advertising and market research",
    "74": "Other professional, scientific and technical activities",
    "75": "Veterinary activities",
    "77": "Rental and leasing activities",
    "78": "Employment activities",
    "79": "Travel agency and tour operator activities",
    "80": "Security and investigation activities",
    "81": "Services to buildings and landscape activities",
    "82": "Office administrative and support activities",
    "84": "Public administration and defence",
    "85": "Education",
    "86": "Human health activities",
    "87": "Residential care activities",
    "88": "Social work activities without accommodation",
    "90": "Creative, arts and entertainment activities",
    "91": "Libraries, archives, museums and other cultural activities",
    "92": "Gambling and betting activities",
    "93": "Sports activities and amusement and recreation activities",
    "94": "Activities of membership organisations",
    "95": "Repair of computers and personal and household goods",
    "96": "Other personal service activities",
    "97": "Activities of households as employers of domestic personnel",
    "98": "Undifferentiated goods- and services-producing activities",
    "99": "Activities of extraterritorial organisations and bodies",
}


def get_section(nace_2digit: str) -> tuple[str, str] | None:
    """Return (letter_section, section_name) for a 2-digit NACE code, or None."""
    return NACE_2DIGIT.get(nace_2digit.strip().zfill(2))


def get_division_name(nace_2digit: str) -> str:
    """Return human-readable division name for a 2-digit NACE code."""
    code = nace_2digit.strip().zfill(2)
    return NACE_DIVISION_NAMES.get(code, f"NACE {code}")


def normalize_nace(raw: str) -> str | None:
    """Normalize a NACE code string to 2-digit format, or None if invalid.

    Accepts: "29", "29.10", "1", "01", "C29", "c 29", "NACE:29"
    Returns: zero-padded 2-digit string like "29" or "01", or None if unknown.
    """
    import re
    cleaned = re.sub(r"[^0-9]", "", raw.strip())
    if not cleaned:
        return None
    # zero-pad to 2 digits and check
    code = cleaned[:2].zfill(2)
    if code in NACE_2DIGIT:
        return code
    return None


ALL_NACE_2DIGIT_CODES: list[str] = sorted(NACE_2DIGIT.keys())
