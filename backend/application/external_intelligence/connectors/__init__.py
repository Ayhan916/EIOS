"""M34.1 Live Connector Framework."""

from .base import BaseLiveConnector, ConnectorRunResult, run_with_retry
from .eu_sanctions import EUSanctionsConnector
from .ilo import ILOConnector
from .transparency_international import TransparencyInternationalConnector
from .un_sanctions import UNSanctionsConnector
from .unicef import UNICEFConnector
from .world_bank import WorldBankConnector

ALL_CONNECTORS: list[type[BaseLiveConnector]] = [
    WorldBankConnector,
    TransparencyInternationalConnector,
    ILOConnector,
    UNICEFConnector,
    UNSanctionsConnector,
    EUSanctionsConnector,
]

__all__ = [
    "BaseLiveConnector",
    "ConnectorRunResult",
    "run_with_retry",
    "WorldBankConnector",
    "TransparencyInternationalConnector",
    "ILOConnector",
    "UNICEFConnector",
    "UNSanctionsConnector",
    "EUSanctionsConnector",
    "ALL_CONNECTORS",
]
