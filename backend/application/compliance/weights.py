"""
Regulatory Exposure Weights

Each article is assigned a weight (0.0–1.0) representing how severe a compliance
gap would be from a regulatory enforcement and reputational standpoint.

Weights reflect:
  - Binding vs. voluntary nature
  - Enforcement history and penalty exposure
  - Proximity to fundamental rights (child/forced labour score higher)
  - Foundational vs. procedural nature of the obligation
"""

from __future__ import annotations

REGULATORY_EXPOSURE: dict[str, float] = {
    # CSDDD — all mandatory; foundational identification/prevention obligations score highest
    "CSDDD-Art-5": 0.85,  # due diligence policy — foundational governance obligation
    "CSDDD-Art-6": 1.00,  # identification of adverse impacts — core CSDDD obligation
    "CSDDD-Art-7": 1.00,  # prevention/mitigation — core CSDDD obligation
    "CSDDD-Art-8": 0.95,  # bringing impacts to an end
    "CSDDD-Art-9": 0.90,  # remediation
    "CSDDD-Art-10": 0.80,  # grievance mechanisms
    "CSDDD-Art-11": 0.75,  # monitoring effectiveness
    "CSDDD-Art-12": 0.70,  # public reporting
    "CSDDD-Art-22": 0.85,  # directors' duty of care for sustainability
    # LkSG — German Supply Chain Act; all mandatory with financial penalties
    "LkSG-3": 0.90,  # due diligence obligations — overarching obligation
    "LkSG-4": 1.00,  # risk analysis — required first step; penalties start here
    "LkSG-5": 0.95,  # preventive measures in own operations and supply chain
    "LkSG-6": 0.90,  # remediation measures when violations confirmed
    "LkSG-7": 0.80,  # complaint mechanisms for affected parties
    "LkSG-8": 0.75,  # documentation and annual reporting obligation
    "LkSG-10": 0.80,  # indirect supplier due diligence (triggered by substantiated knowledge)
    # ESRS — mandatory under CSRD; environmental topics
    "ESRS-E1": 0.90,  # climate change — high political visibility; Scope 3 mandatory
    "ESRS-E2": 0.75,  # pollution
    "ESRS-E3": 0.75,  # water and marine resources
    "ESRS-E4": 0.75,  # biodiversity and ecosystems
    "ESRS-E5": 0.70,  # resource use and circular economy
    # ESRS — social topics; value chain workers especially high-risk
    "ESRS-S1": 0.80,  # own workforce
    "ESRS-S2": 0.90,  # workers in the value chain — forced/child labour exposure
    "ESRS-S3": 0.75,  # affected communities
    "ESRS-G1": 0.80,  # business conduct / anti-corruption
    # GRI — recommended; weights reflect human rights salience
    "GRI-2": 0.55,  # general disclosures
    "GRI-303": 0.55,  # water and effluents
    "GRI-304": 0.55,  # biodiversity
    "GRI-305": 0.65,  # GHG emissions — increasingly used in litigation
    "GRI-403": 0.60,  # occupational health and safety
    "GRI-408": 0.80,  # child labor — elevated even for voluntary standard
    "GRI-409": 0.80,  # forced or compulsory labor
    "GRI-414": 0.65,  # supplier social assessment
}

_DEFAULT_EXPOSURE = 0.60


def exposure(article_code: str) -> float:
    return REGULATORY_EXPOSURE.get(article_code, _DEFAULT_EXPOSURE)
