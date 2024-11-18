# -*- encoding: utf-8 -*-
"""
SALLY
sally.handlers.vlei module

Handle vLEI Ecosystem credential types
"""
from keri import help, kering
logger = help.ogler.getLogger()

QVI_SCHEMA = "EBfdlu8R27Fbx-ehrqwImnK-8Cm79sqbAQ4MmvEAYqao"
LE_SCHEMA = "ENPXp1vQzRF6JwIuS-mp2U8Uf1MoADoP_GqQ62VsDZWY"
OOR_AUTH_SCHEMA = "EKA57bKBKxr_kN7iN5i7lMUxpMG-s19dRcmov1iDxz-E"
OOR_SCHEMA = "EBNaNu-M9P5cgrnfl2Fvymy4E_jvxxyjb70PRtiANlJy"

class VLEIHandler:
    def __init__(self, mappings, reger, auth):
        self.mappings = mappings
        self.reger = reger
        self.auth = auth


    def validateQualifiedvLEIIssuer(self, creder):
        """ Validate issuer of QVI against known valid issuer

        Parameters:
            creder (Creder): QVI credential to validate

        Raises:
            ValidationError: If credential was not issued from known valid issuer

        """
        if creder.schema != QVI_SCHEMA:
            raise kering.ValidationError(
                f"invalid schema {creder.schema} for QVI credential {creder.said}")

        if not creder.issuer == self.auth:
            raise kering.ValidationError("QVI credential not issued by known valid issuer")


    def validateLegalEntity(self, creder):
        if creder.schema != LE_SCHEMA:
            raise kering.ValidationError(
                f"invalid schema {creder.schema} for LE credential {creder.said}")

        self.validateQVIChain(creder)


    def validateOfficialRoleAuth(self, creder):
        if creder.schema != OOR_AUTH_SCHEMA:
            raise kering.ValidationError(
                f"invalid schema {creder.schema} for OOR credential {creder.said}")

        edges = creder.edge
        lesaid = edges["le"]["n"]
        le = self.reger.creds.get(lesaid)
        if le is None:
            raise kering.ValidationError(
                f"LE credential {lesaid} not found for AUTH credential {creder.said}")

        self.validateLegalEntity(le)


    def validateOfficialRole(self, creder):
        if creder.schema != OOR_SCHEMA:
            raise kering.ValidationError(
                f"invalid schema {creder.schema} for OOR credential {creder.said}")

        edges = creder.edge
        asaid = edges["auth"]["n"]
        auth = self.reger.creds.get(asaid)
        if auth is None:
            logger.error(f"AUTH credential {asaid} not found for OOR credential {creder.said}")
            raise kering.ValidationError(
                f"AUTH credential {asaid} not found for OOR credential {creder.said}")

        if auth.sad["a"]["AID"] != creder.attrib["i"]:
            raise kering.ValidationError(
                f"invalid issuee {creder.attrib['i']}  doesnt match AUTH value of "
                f"{auth.sad['a']['AID']} for OOR " f"credential {creder.said}")

        if auth.sad["a"]["personLegalName"] != creder.attrib["personLegalName"]:
            raise kering.ValidationError(
                f"invalid personLegalNAme {creder.attrib['personLegalName']} for OOR "
                f"credential {creder.said}")

        if auth.sad["a"]["officialRole"] != creder.attrib["officialRole"]:
            raise kering.ValidationError(
                f"invalid role {creder.attrib['officialRole']} for OOR credential"
                f" {creder.said}")

        self.validateOfficialRoleAuth(auth)


    def validateQVIChain(self, creder):
        edges = creder.edge
        qsaid = edges["qvi"]["n"]
        qcreder = self.reger.creds.get(qsaid)
        if qcreder is None:
            raise kering.ValidationError(
                f"QVI credential {qsaid} not found for credential {creder.said}")

        self.validateQualifiedvLEIIssuer(qcreder)


    @staticmethod
    def qviPayload(creder):
        a = creder.sad["a"]
        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            LEI=a["LEI"]
        )

        return data


    @staticmethod
    def entityPayload(creder):
        a = creder.sad["a"]
        edges = creder.edge
        qsaid = edges["qvi"]["n"]
        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            qviCredential=qsaid,
            LEI=a["LEI"]
        )

        return data


    @staticmethod
    def roleCredentialPayload(reger, creder):
        a = creder.sad["a"]
        edges = creder.edge
        asaid = edges["auth"]["n"]

        auth = reger.creds.get(asaid)
        aedges = auth.edge
        lesaid = aedges["le"]["n"]
        qvi = reger.creds.get(lesaid)
        qedges = qvi.edge
        qsaid = qedges["qvi"]["n"]

        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            authCredential=asaid,
            qviCredential=qsaid,
            legalEntityCredential=lesaid,
            LEI=a["LEI"],
            personLegalName=a["personLegalName"],
            officialRole=a["officialRole"]
        )

        return data
