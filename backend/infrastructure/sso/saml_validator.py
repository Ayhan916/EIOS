"""Production SAML 2.0 assertion validator (M45.1 — G-002).

Uses lxml for XML parsing and signxml for XML Digital Signature verification.
Validates: signature, issuer, NotBefore/NotOnOrAfter conditions, AudienceRestriction.
Extracts: NameID, email, displayName, and group attributes.

Implements the SAMLAssertionValidator Protocol from application.enterprise.sso_validation.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime

import lxml.etree as etree
from signxml import InvalidInput, InvalidSignature, XMLVerifier

from application.enterprise.sso_validation import SSOValidationError, ValidatedIdentity

_NS_ASSERTION = "urn:oasis:names:tc:SAML:2.0:assertion"
_NS_PROTOCOL = "urn:oasis:names:tc:SAML:2.0:protocol"

# Standard attribute OIDs / names for email and display name
_EMAIL_ATTRS = frozenset(
    {
        "email",
        "mail",
        "urn:oid:0.9.2342.19200300.100.1.3",  # eduPersonPrincipalName
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    }
)
_DISPLAYNAME_ATTRS = frozenset(
    {
        "displayName",
        "cn",
        "urn:oid:2.16.840.1.113730.3.1.241",  # displayName OID
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    }
)


class ProductionSAMLValidator:
    """SAML 2.0 Assertion Consumer Service validator."""

    def validate(
        self,
        saml_response: str,
        idp_issuer: str,
        sp_entity_id: str,
        acs_url: str,
        certificates: list[str],
        group_attribute: str = "groups",
    ) -> ValidatedIdentity:
        try:
            xml_bytes = base64.b64decode(saml_response)
        except Exception as exc:
            raise SSOValidationError("SAMLResponse is not valid base64") from exc

        try:
            root = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as exc:
            raise SSOValidationError(f"SAMLResponse XML parse error: {exc}") from exc

        # Try each certificate until signature verifies
        signed_root = self._verify_signature(root, certificates)

        assertion = self._extract_assertion(signed_root)
        self._check_issuer(assertion, idp_issuer)
        self._check_conditions(assertion, sp_entity_id)

        name_id = self._extract_name_id(assertion)
        email, display_name, groups = self._extract_attributes(assertion, name_id, group_attribute)

        return ValidatedIdentity(
            external_id=name_id,
            email=email,
            groups=groups,
            issuer=idp_issuer,
            idp_id="",  # caller sets this after validation
            display_name=display_name,
        )

    def _verify_signature(self, root: etree._Element, certificates: list[str]) -> etree._Element:
        verifier = XMLVerifier()
        last_exc: Exception | None = None
        for cert_pem in certificates:
            try:
                result = verifier.verify(root, x509_cert=cert_pem.strip())
                return result.signed_xml
            except (InvalidSignature, InvalidInput, Exception) as exc:
                last_exc = exc
        raise SSOValidationError(f"SAMLResponse signature invalid: {last_exc}")

    def _extract_assertion(self, signed_root: etree._Element) -> etree._Element:
        tag_assertion = f"{{{_NS_ASSERTION}}}Assertion"
        if signed_root.tag == tag_assertion:
            return signed_root
        assertions = signed_root.findall(f"{{{_NS_ASSERTION}}}Assertion")
        if not assertions:
            raise SSOValidationError("No Assertion element found in SAMLResponse")
        return assertions[0]

    def _check_issuer(self, assertion: etree._Element, idp_issuer: str) -> None:
        issuer_elem = assertion.find(f"{{{_NS_ASSERTION}}}Issuer")
        actual = issuer_elem.text if issuer_elem is not None else None
        if actual != idp_issuer:
            raise SSOValidationError(f"Issuer mismatch: expected '{idp_issuer}', got '{actual}'")

    def _check_conditions(self, assertion: etree._Element, sp_entity_id: str) -> None:
        conditions = assertion.find(f"{{{_NS_ASSERTION}}}Conditions")
        if conditions is None:
            return

        now = datetime.now(UTC)

        not_before_str = conditions.get("NotBefore")
        if not_before_str:
            not_before = datetime.fromisoformat(not_before_str.replace("Z", "+00:00"))
            if now < not_before:
                raise SSOValidationError("SAMLResponse is not yet valid (NotBefore)")

        not_on_or_after_str = conditions.get("NotOnOrAfter")
        if not_on_or_after_str:
            not_on_or_after = datetime.fromisoformat(not_on_or_after_str.replace("Z", "+00:00"))
            if now >= not_on_or_after:
                raise SSOValidationError("SAMLResponse has expired (NotOnOrAfter)")

        if sp_entity_id:
            audience_restrictions = conditions.findall(f"{{{_NS_ASSERTION}}}AudienceRestriction")
            if audience_restrictions:
                valid = any(
                    aud.text == sp_entity_id
                    for ar in audience_restrictions
                    for aud in ar.findall(f"{{{_NS_ASSERTION}}}Audience")
                )
                if not valid:
                    raise SSOValidationError(f"Audience restriction: expected '{sp_entity_id}'")

    def _extract_name_id(self, assertion: etree._Element) -> str:
        subject = assertion.find(f"{{{_NS_ASSERTION}}}Subject")
        if subject is not None:
            name_id_elem = subject.find(f"{{{_NS_ASSERTION}}}NameID")
            if name_id_elem is not None and name_id_elem.text:
                return name_id_elem.text
        raise SSOValidationError("No NameID found in SAML assertion Subject")

    def _extract_attributes(
        self,
        assertion: etree._Element,
        name_id: str,
        group_attribute: str,
    ) -> tuple[str, str | None, list[str]]:
        email = name_id
        display_name: str | None = None
        groups: list[str] = []

        attr_stmt = assertion.find(f"{{{_NS_ASSERTION}}}AttributeStatement")
        if attr_stmt is None:
            return email, display_name, groups

        for attr in attr_stmt.findall(f"{{{_NS_ASSERTION}}}Attribute"):
            attr_name = attr.get("Name", "")
            values: list[str] = [
                v.text or "" for v in attr.findall(f"{{{_NS_ASSERTION}}}AttributeValue")
            ]
            if attr_name in _EMAIL_ATTRS and values:
                email = values[0]
            elif attr_name in _DISPLAYNAME_ATTRS and values:
                display_name = values[0]
            elif attr_name == group_attribute:
                groups = [v for v in values if v]

        return email, display_name, groups
