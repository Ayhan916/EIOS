# DOMAIN_MODEL.md — Fachliches Domänenmodell
**Status: APPROVED — Version 1.0 (2026-07-09)**
**Authority: Lead AI Architect**
**Change Control: ADR erforderlich für jede Änderung an Aggregaten, Entities oder Domain Events**

---

## Überblick

Das Domänenmodell ist technologie-agnostisch. Es beschreibt die fachliche Realität — nicht PostgreSQL-Tabellen oder FastAPI-Endpunkte.

### Die 7 Bounded Contexts

```
1. ORGANISATION          → Wer sind wir? Wer liefert uns?
2. LIEFERKETTE           → Wie sind wir verbunden?
3. RISIKO & INTELLIGENCE → Was wissen wir über Risiken?  [KERN]
4. REGULIERUNG           → Was müssen wir gesetzlich tun?
5. ASSESSMENT            → Wie untersuchen wir systematisch?
6. MASSNAHMEN            → Was tun wir dagegen?
7. BERICHTERSTATTUNG     → Was kommunizieren wir?

Querschnitt: WISSEN & EVIDENZ → Woher wissen wir das?
```

---

## Ubiquitous Language (verbindliches Vokabular)

| Begriff | Definition | Abgrenzung |
|---------|-----------|-----------|
| **Signal** | Unverifikierter Hinweis aus externer Quelle | Noch keine Bewertung, kein Entity-Link garantiert |
| **Finding** | Bestätigter, einer Entität zugeordneter Befund | Hat immer ≥1 EvidenceRef |
| **Risk** | Identifiziertes, bewertetes, aktiv gesteuertes Risikoobjekt | Überlebt individuelle Assessments |
| **Incident** | Eingetretener, bestätigter Schadensfall | Löst Remedy-Pflicht aus |
| **Obligation** | Konkrete gesetzliche Handlungspflicht aus einem Artikel | Unveränderlich (aus Gesetz abgeleitet) |
| **ComplianceGap** | Lücke zwischen Obligation und aktuellem Stand | Veränderlich (kann geschlossen werden) |
| **Control** | Präventive Maßnahme gegen ein Risiko | Wird auf Wirksamkeit getestet |
| **Remedy** | Wiedergutmachung nach eingetretenem Schaden | CSDDD Art. 11 — rechtlich bindend |
| **Evidence** | Nachweismaterial für eine Behauptung | Hat Quelle, Zeitstempel, Reliability |
| **Assessment** | Formaler, methodisch strukturierter Prüfprozess | Hat Scope, Lifecycle, Genehmigung |
| **ConfidenceCard** | Strukturierte Konfidenzbegründung | Kein einzelner float-Wert |
| **RiskScore** | Versioniertes, deterministisches Bewertungsergebnis | Keine LLM-Schätzung |
| **Tier** | Position in der Lieferkette (1=direkt, 2=indirekt etc.) | Bestimmt Sorgfaltspflicht-Tiefe |
| **AuditPackage** | Vollständiger Prüfungsnachweis (reproduzierbar) | Enthält Methodik, Formeln, Hash-Kette |

---

## Bounded Context 1 — Organisation

### Aggregate: LegalEntity
**Invariante:** Exakt eine Jurisdiktion. Mitarbeiterzahl + Umsatz bestimmen CSDDD-Anwendbarkeit.

```
LegalEntity                                Entity (hat Identität)
├── legalName: str
├── aliases: list[str]
├── registrationNumber: str
├── jurisdiction: Jurisdiction             Value Object
├── legalForm: LegalForm
├── employees: EmployeeRange               Value Object
├── netTurnover: TurnoverRange             Value Object
├── industryCodes: list[NACECode]
├── ultimateParent: LegalEntityId?
├── status: EntityStatus
└── facilities: list[Facility]             Teil des Aggregats

Facility                                   Teil von LegalEntity
├── name: str
├── facilityType: FacilityType
├── address: Address                       Value Object
├── country: CountryCode
├── employees: int
├── commodities: list[CommodityCode]
└── certifications: list[Certification]    Value Object
```

### Aggregate: CompanyProfile
Konsolidierte Sicht auf ein Unternehmen (kann mehrere LegalEntities umfassen).

```
CompanyProfile                             Aggregate Root
├── canonicalName: str
├── legalEntities: list[LegalEntityId]
├── headquartersCountry: CountryCode
├── primarySector: SectorCode
├── supplyChainPosition: Position
├── publiclyListed: bool
├── parentCompany: CompanyProfileId?
└── subsidiaries: list[CompanyProfileId]
```

### Domain Events
- `EntityThresholdCrossed { entityId, threshold, value }` → triggert CSDDD-Prüfung
- `FacilityAddedToHighRiskCountry { entityId, facilityId, countryRisk }`

---

## Bounded Context 2 — Lieferkette

### Aggregate: SupplyChainNetwork
**Invariante:** Kein Cycle erlaubt (A→B→A).

```
SupplyChainRelationship                    Entity (Kante im Graph)
├── buyer: CompanyProfileId
├── supplier: CompanyProfileId
├── tier: Tier                             1 | 2 | 3 | Unknown
├── relationshipType: RelationshipType     DirectMaterial | IndirectService | SubContractor
├── commodities: list[Commodity]
├── annualSpend: MonetaryValue?
├── contractStatus: ContractStatus
├── discoveryMethod: DiscoveryMethod       SelfDeclared | Inferred | ExternalDB
├── dataConfidence: Confidence
├── validFrom: Date
└── validUntil: Date?
```

### Aggregate: Supplier
Perspektive auf ein Unternehmen als Lieferant. Referenziert CompanyProfile (kein Import).

```
Supplier                                   Aggregate Root
├── companyRef: CompanyProfileId           Referenz, kein Aggregat-Import
├── supplierStatus: SupplierStatus         Approved | Probationary | Suspended
├── riskProfile: SupplierRiskProfile       Value Object
│   ├── inherentRiskScore: float           vor Kontrollen
│   ├── residualRiskScore: float           nach Kontrollen
│   ├── countryExposure: float
│   ├── sectorExposure: float
│   └── lastAssessedAt: datetime
├── criticalityLevel: CriticalityLevel     Critical | High | Medium | Low
└── alternativeSuppliers: int
```

### Domain Events
- `SupplierOnboarded { supplierId, tier, commodities }`
- `Tier2SupplierDiscovered { buyerId, tier1Id, tier2Id, method }`
- `SupplierRiskLevelChanged { supplierId, oldLevel, newLevel }`

---

## Bounded Context 3 — Risiko & Intelligence (KERN)

### Die drei Stufen der Risikointelligenz

```
Signal (unverifiziert)
  ↓ Klassifikation + Entity-Linking
Finding (verifiziert, mit Evidence)
  ↓ RiskScore-Berechnung
Risk (gesteuert, mit Lifecycle)
```

**Invariante (ADR-013):** Keine Abkürzungen. Signal → Risk direkt ist verboten.

---

### Aggregate: Signal

```
Signal                                     Aggregate Root
├── signalType: SignalType
│   LaborDispute | EnvironmentalIncident | FinancialDistress |
│   RegulatoryViolation | HumanRightsAllegation | ProductRecall |
│   SupplyChainDisruption | LeadershipChange | LitigationFiled | SanctionsImposed
├── dimension: Dimension                   Social | Environmental | Governance | Economic
├── direction: Direction                   Negative | Positive | Neutral
├── severity: Severity                     Critical | High | Medium | Low
├── confidence: Confidence                 Verified | Probable | Possible | Rumor
├── affectedRights: list[HumanRight]
├── subjectRef: EntityReference
├── geographicScope: list[Location]
├── source: SignalSource                   Value Object
│   ├── sourceType: SourceType             NGO | News | Government | InternalAudit
│   ├── sourceName: str
│   ├── sourceUrl: URI?
│   ├── reliability: Reliability           Tier1 | Tier2 | Tier3 | Unknown
│   └── publishedAt: datetime
├── observedAt: datetime
├── status: SignalStatus
│   Received | Classified | Linked | Evaluated | Escalated | Dismissed
└── canonicalEventId: EventId?            Duplikate geclustert
```

---

### Aggregate: Finding
**Invariante (ADR-003):** Mindestens eine EvidenceRef ist Pflicht.

```
Finding                                    Aggregate Root
├── title: str
├── description: str
├── category: FindingCategory
│   HumanRights | Environment | Governance | Labour | SupplyChain | FinancialIntegrity
├── severity: Severity
├── severityMethod: SeverityMethod         MLClassifier | HumanReview | RuleEngine
├── confidence: ConfidenceCard             Value Object (ADR-015)
├── affectedRights: list[HumanRight]
├── entityRef: EntityReference
├── geographicScope: list[Location]
├── period: Period                         Value Object
├── status: FindingStatus
│   Identified | Confirmed | Contested | Remediated | Closed | Reopened
├── supportingEvidence: list[EvidenceRef]  MINIMUM 1 (Invariante)
├── contradictingEvidence: list[EvidenceRef]
├── sourcedFrom: list[SignalRef]
└── obligationMappings: list[ObligationMapping]
    └── {obligationRef, confidence, method, approvedBy}
```

---

### Aggregate: Risk
**Invariante:** Kein Risk ohne Score. Kein Risk ohne Finding. Closed Risk nur durch Signal reopenbar.

```
Risk                                       Aggregate Root
├── title: str
├── description: str
├── riskCategory: RiskCategory
├── affectedDimension: Dimension
├── entityRef: EntityReference
├── supplyChainScope: SupplyChainScope
│   ├── affectedTiers: list[Tier]
│   └── estimatedReach: int
├── compositeRiskScore: RiskScore          Value Object (ADR-002)
│   ├── severity: float                    0–1
│   ├── likelihood: float                  0–1
│   ├── sourceReliability: float           0–1
│   ├── evidenceStrength: float            0–1
│   ├── temporalTrend: float               -1 bis +1
│   ├── geographicExposure: float          0–1
│   ├── sectorExposure: float              0–1
│   ├── dataCompleteness: float            0–1
│   ├── composite: float                   gewichtete Summe
│   ├── formulaVersion: str                "RiskScore-v1.0"
│   ├── calculatedAt: datetime
│   └── factorBreakdown: dict              für Explainability
├── contributingFindings: list[FindingRef]  MINIMUM 1 (Invariante)
├── controlsInPlace: list[ControlRef]
└── status: RiskStatus                     (siehe Lifecycle)
```

### Risk Lifecycle (vereinfacht)

```
[IDENTIFIED] → [ASSESSED] → [MONITORED] oder [ESCALATED]
                              ↓
                         [IN_TREATMENT]
                              ↓
                    [MITIGATED] oder [ACCEPTED]
                              ↓
                          [CLOSED]
           (neue Signale können REOPENED auslösen)
```

---

### Value Object: ConfidenceCard (ADR-015)

```python
@dataclass(frozen=True)
class ConfidenceCard:
    overall_level: ConfidenceLevel         # HIGH | MEDIUM | LOW
    source_count: int
    source_independence: float             # 0–1
    source_recency_days: int
    data_completeness: float               # 0–1
    cross_validation_score: float          # 0–1
    contradiction_penalty: float           # Abzug
    missing_information: list[str]         # explizite Lücken
    uncertainty_notes: list[str]
    calculated_at: datetime
```

---

## Bounded Context 4 — Regulierung & Compliance

### Aggregate: Regulation

```
Regulation                                 Aggregate Root
├── name: str                              "CSDDD"
├── type: RegulationType                   EUDirective | NationalLaw | Standard
├── jurisdiction: Jurisdiction
├── effectiveDate: Date
├── applicabilityThresholds: list[Threshold]
│   EmployeeThreshold | TurnoverThreshold | SectorThreshold
├── status: RegulationStatus
└── articles: list[Article]               Teil des Aggregats

Article
├── articleNumber: str                     "Art. 8"
├── title: str
├── obligationType: ObligationType         Identify | Prevent | Mitigate | Remedy | Disclose
├── affectedDimensions: list[Dimension]
└── targetGroup: TargetGroup              OwnOperations | DirectSuppliers | All
```

### Aggregate: Obligation
**Das zentrale Objekt für CSDDD-Compliance. Unveränderlich — abgeleitet aus Gesetz.**

```
Obligation                                 Aggregate Root
├── derivedFrom: ArticleRef
├── obligationText: str                    konkrete Handlungspflicht
├── evidenceRequirements: list[EvidenceRequirement]
│   ├── type: EvidenceType                Document | Audit | Certification | Process
│   ├── minimumFrequency: Frequency
│   └── minimumQuality: Quality
├── applicabilityConditions: list[Condition]
└── reportingObligation: bool
```

### Aggregate: ComplianceStatus

```
ComplianceGap                              Entity
├── company: CompanyProfileRef
├── obligation: ObligationRef
├── gapType: GapType                       NotAssessed | NonCompliant | Partial | Compliant | Exempt
├── gapSeverity: Severity
├── identifiedAt: datetime
├── identificationMethod: Method           RuleEngine | Assessment | ExternalAudit
├── remediationRequired: bool
├── targetComplianceDate: Date?
└── evidenceProvided: list[EvidenceRef]
```

### Domain Events
- `ComplianceGapIdentified { gapId, obligationId, entityId, severity }`
- `ComplianceGapClosed { gapId, closingEvidence }`
- `ObligationActivated { obligationId, entityId, reason }`

---

## Bounded Context 5 — Assessment & Due Diligence

### Aggregate: Assessment
**Invariante (ADR-014):** Nach Genehmigung unveränderlich.

```
Assessment                                 Aggregate Root
├── title: str
├── assessmentType: AssessmentType
│   InitialDueDiligence | AnnualReview | IncidentTriggered | ThirdPartyAudit
├── scope: AssessmentScope                 Value Object
│   ├── entity: EntityReference
│   ├── topics: list[AssessmentTopic]
│   ├── geographies: list[Location]
│   ├── supplyChainTiers: list[Tier]
│   └── period: Period
├── methodology: Methodology               UNGP | ISO31000 | GRI | CSDDD | Custom
├── status: AssessmentStatus
│   Initiated | DataCollection | Analysis | UnderReview | Approved | Archived
├── assignedTo: UserId
├── approvedBy: UserId?                    Menschliche Genehmigung (ADR-005)
├── approvalDate: datetime?
├── findings: list[Finding]               im Assessment erstellte Befunde
├── risks: list[Risk]
├── evidence: list[EvidenceRef]
└── recommendations: list[Recommendation]
```

### Assessment Lifecycle

```
[Initiated] → [DataCollection] → [Analysis] → [UnderReview] → [Approved] → [Archived]
                                                     ↑
                                              Human-in-the-Loop Gate (ADR-005)
                                              KI darf hier NICHT autonom entscheiden
```

---

## Bounded Context 6 — Maßnahmen & Kontrollen

### Aggregate: Control

```
Control                                    Aggregate Root
├── controlType: ControlType               Preventive | Detective | Corrective
├── controlMechanism: Mechanism            Policy | Audit | Certification | Training
├── appliesTo: EntityScope
├── addressesRiskCategories: list[RiskCategory]
├── effectiveness: Effectiveness           High | Medium | Low | NotTested
├── lastTestedAt: datetime?
└── status: ControlStatus                  Active | UnderReview | Suspended | Retired
```

### Aggregate: MitigationPlan

```
MitigationPlan                             Aggregate Root
├── addressesRisk: RiskRef
├── planType: PlanType                     Prevention | Mitigation | Remedy
├── expectedRiskReduction: float
├── measures: list[MitigationMeasure]
├── sponsor: PersonRef
└── status: PlanStatus                     Draft | Approved | Active | Completed

MitigationMeasure                          Entity
├── measureType: MeasureType               PolicyChange | AuditRequirement | SourcingChange
├── assignedTo: UserId
├── dueDate: Date
├── completionEvidence: EvidenceRef?
└── status: MeasureStatus                  Planned | InProgress | Completed | Overdue
```

### Aggregate: Remedy (CSDDD Art. 11)
**Distinkt von Mitigation: Remedy = Wiedergutmachung nach eingetretenem Schaden.**

```
Remedy                                     Aggregate Root
├── triggeredByFinding: FindingRef
├── affectedParties: list[AffectedParty]
├── remedyType: RemedyType
│   FinancialCompensation | Restitution | Rehabilitation | Satisfaction
├── remedyStatus: RemedyStatus             Required | InNegotiation | Implemented
└── stakeholderEngagement: StakeholderEngagementProcess
```

---

## Bounded Context — Wissen & Evidenz (Querschnitt)

### Aggregate: Document
**Invariante:** Unveränderlich nach Ingestion.

```
Document                                   Aggregate Root
├── documentType: DocType
│   AnnualReport | SustainabilityReport | NewsArticle | NGOReport | AuditReport
├── documentClass: DocClass                Financial | ESG | Regulatory | Statement | Signal
├── subjectRef: EntityReference
├── reportingPeriod: Period?
├── source: DocumentSource                 Value Object
│   ├── sourceName: str
│   ├── sourceUrl: URI?
│   ├── sourceType: SourceType
│   └── reliability: Reliability
├── publishedAt: datetime
├── qualityScore: float
└── extractedFacts: list[ExtractedFact]
```

### Value Objects: KnowledgeFact

```
QuantitativeFact
├── factType: FactType                     Revenue | CO2Scope1 | Employees | ...
├── value: Decimal
├── unit: Unit                             EUR_M | tCO2 | GWh | PCT | COUNT
├── period: Period
├── confidence: FactConfidence             Exact | Estimated | Calculated
└── sourceDocument: DocumentRef

QualitativeFact
├── factType: QualFactType                 Commitment | Target | PolicyStatement
├── description: str
├── targetYear: int?
└── dimension: Dimension
```

---

## Bounded Context 7 — Berichterstattung & Audit

### Aggregate: Report
**Invariante:** Nach Genehmigung unveränderlich.

```
Report                                     Aggregate Root
├── reportType: ReportType
│   DueDiligenceReport | ExecutiveSummary | RegulatoryDisclosure | AuditPackage
├── scope: ReportScope
├── period: Period
├── audience: Audience                     Board | Management | Auditor | Regulator | Public
├── evidenceBundle: list[EvidenceRef]
├── findingsSummary: list[FindingRef]
├── risksSummary: list[RiskRef]
└── status: ReportStatus                   Draft | UnderReview | Approved | Published
```

### Aggregate: AuditPackage
**Vollständiger Nachweis für externe Prüfung — reproduzierbar, manipulationsresistent.**

```
AuditPackage                               Aggregate Root
├── subject: EntityReference
├── period: Period
├── methodology: MethodologyRecord
│   ├── riskScoringFormula: FormulaVersion
│   ├── mlModelsUsed: list[ModelVersion]
│   ├── promptsUsed: list[PromptVersion]
│   └── dataSourceVersions: list[DatasetVersion]
├── evidenceInventory: list[EvidenceRecord]
├── decisionLog: list[DecisionRecord]
├── humanDecisions: list[HumanDecisionRecord]
└── integrityHash: SHA256                  Hash über alle Inhalte (ADR-006)
```

---

## Vollständige Domain Events (alle Contexts)

```
Organisation:
  EntityThresholdCrossed       { entityId, threshold, value }
  FacilityAddedToHighRisk      { entityId, facilityId, countryRisk }

Lieferkette:
  SupplierOnboarded            { supplierId, tier, commodities }
  Tier2SupplierDiscovered      { buyerId, tier1Id, tier2Id, method }
  SupplierRiskLevelChanged     { supplierId, oldLevel, newLevel }
  SupplierRelationshipEnded    { supplierId, reason, effectiveDate }

Risiko & Intelligence:
  SignalReceived               { signalId, signalType, severity, sourceRef }
  SignalLinkedToEntity         { signalId, entityRef, method, confidence }
  FindingCreated               { findingId, severity, entityRef }
  RiskIdentified               { riskId, category, compositeScore }
  RiskScoreChanged             { riskId, oldScore, newScore, reason }
  RiskEscalated                { riskId, fromStatus, reason }
  RiskClosed                   { riskId, resolution }
  ContradictionDetected        { finding1, finding2, description }

Regulierung & Compliance:
  ObligationActivated          { obligationId, entityId, reason }
  ComplianceGapIdentified      { gapId, obligationId, entityId, severity }
  ComplianceGapClosed          { gapId, closingEvidence }
  RegulationAmended            { regulationId, version, effectiveDate }

Assessment & Due Diligence:
  AssessmentInitiated          { assessmentId, scope, methodology }
  AssessmentApproved           { assessmentId, approvedBy, findingCount }
  FindingContested             { findingId, contestedBy, reason }
  HumanReviewRequired          { assessmentId, reason, deadline }

Maßnahmen & Kontrollen:
  MitigationPlanCreated        { planId, riskId, targetReduction }
  MeasureOverdue               { measureId, planId, daysOverdue }
  ControlEffectivenessLost     { controlId, lastTestedAt }
  RemedyRequired               { remediationId, findingId, affectedParties }

Berichterstattung & Audit:
  ReportPublished              { reportId, reportType, audience }
  AuditPackageGenerated        { packageId, integrityHash }
```

---

*Dieses Dokument ist die authoritative Quelle des Domänenmodells. Code und Tests müssen diesem Modell folgen, nicht umgekehrt.*
