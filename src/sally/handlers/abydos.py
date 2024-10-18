# -*- encoding: utf-8 -*-
"""
SALLY
sally.handlers.abydos module

Handle Abydos Tutorial credential types
"""
from keri import kering

from sally.handlers import mappings

JOURNEY_TYPE = 'TreasureHuntingJourney'
REQUEST_TYPE = 'JourneyMarkRequest'
MARK_TYPE = 'JourneyMark'
CHARTER_TYPE = 'JourneyCharter'

class AbydosHandler:
    def __init__(self, schema_mappings, reger, auth):
        self.schema_mappings = schema_mappings
        self.reger = reger
        self.auth = auth

    def validateJourney(self, creder):
        journey_said = mappings.resolve_type_to_said(self.schema_mappings, JOURNEY_TYPE)
        if creder.schema != journey_said:
            raise kering.ValidationError(f'Invalid schema SAID {creder.schema} for {JOURNEY_TYPE} '
                                         f'credential SAID: {journey_said}')

        if not creder.issuer == self.auth:
            raise kering.ValidationError(
                "TreasureHuntingJourney credential not issued by known valid issuer")


    def validateJourneyMarkRequest(self, creder):
        request_said = mappings.resolve_type_to_said(self.schema_mappings, REQUEST_TYPE)
        if creder.schema != request_said:
            raise kering.ValidationError(f'Invalid schema SAID {creder.schema} for {REQUEST_TYPE} '
                                         f'credential SAID: {request_said}')
        self.validateJourneyChain(creder)


    def validateJourneyChain(self, creder):
        edges = creder.chains
        journey_said = edges["journey"]["n"]
        journey_creder = self.reger.creds.get(journey_said)
        if journey_creder is None:
            raise kering.ValidationError(f'{JOURNEY_TYPE} credential not found for {creder.said}')
        self.validateJourney(journey_creder)


    def validateJourneyMark(self, creder):
        request_said = mappings.resolve_type_to_said(self.schema_mappings, MARK_TYPE)
        if creder.schema != request_said:
            raise kering.ValidationError(f'Invalid schema SAID {creder.schema} for {MARK_TYPE} '
                                         f'credential SAID: {request_said}')
        self.validateRequestChain(creder)


    def validateRequestChain(self, creder):
        edges = creder.chains
        request_said = edges["request"]["n"]
        request_creder = self.reger.creds.get(request_said)
        if request_creder is None:
            raise kering.ValidationError(f'{REQUEST_TYPE} credential not found for {creder.said}')
        self.validateJourneyMarkRequest(request_creder)


    def validateJourneyCharter(self, creder):
        request_said = mappings.resolve_type_to_said(self.schema_mappings, CHARTER_TYPE)
        if creder.schema != request_said:
            raise kering.ValidationError(f'Invalid schema SAID {creder.schema} for {MARK_TYPE} '
                                         f'credential SAID: {request_said}')
        if not creder.issuer == self.auth:
            raise kering.ValidationError(
                "JourneyCharter credential not issued by known valid issuer")
        self.validateMarkChain(creder)
        self.validateJourneyChain(creder)


    def validateMarkChain(self, creder):
        edges = creder.chains
        mark_said = edges["mark"]["n"]
        mark_creder = self.reger.creds.get(mark_said)
        if mark_creder is None:
            raise kering.ValidationError(f'{MARK_TYPE} credential not found for {creder.said}')
        # TODO add attribute validation like in validateOfficialRole
        self.validateJourneyMark(mark_creder)

    @staticmethod
    def treasureHuntingJourneyPayload(creder, reger):
        a = creder.crd["a"]
        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            destination=a["destination"],
            treasureSplit=a["treasureSplit"],
            partyThreshold=a["partyThreshold"],
            journeyEndorser=a["journeyEndorser"]
        )

        return data

    @staticmethod
    def journeyMarkRequestPayload(creder, reger):
        a = creder.crd["a"]
        requester_data = a["requester"]
        requester = {
            'firstName': requester_data["firstName"],
            'lastName': requester_data["lastName"],
            'nickname': requester_data["nickname"]
        }
        edges = creder.chains
        journeySaid = edges["journey"]["n"]
        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            requester=requester,
            desiredPartySize=a["desiredPartySize"],
            desiredSplit=a["desiredSplit"],
            journeyCredential=journeySaid
        )

        return data

    @staticmethod
    def journeyMarkPayload(creder, reger):
        a = creder.crd["a"]
        # TODO add in journey credential SAID through reger lookup
        edges = a.chains
        journeySaid = edges["journey"]["n"]

        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            journeyDestination=a["journeyDestination"],
            gatekeeper=a["gatekeeper"],
            negotiatedSplit=a["negotiatedSplit"],
            journeyCredential=journeySaid
        )

        return data

    @staticmethod
    def journeyCharterPayload(creder, reger):
        a = creder.crd["a"]
        edges = creder.chains
        journeySaid = edges["journey"]["n"]
        journey = reger.creds.get(journeySaid)
        jatts = journey.crd["a"]

        markSaid = edges["mark"]["n"]
        mark = reger.creds.get(markSaid)
        requestSaid = mark.chains["request"]["n"]
        request = reger.creds.get(requestSaid)
        ratts = request.crd["a"]

        data = dict(
            schema=creder.schema,
            issuer=creder.issuer,
            issueTimestamp=a["dt"],
            credential=creder.said,
            recipient=a["i"],
            partySize=a["partySize"],
            authorizerName=a["authorizerName"],
            journeyCredential=journeySaid,
            markCredential=markSaid,
            destination=jatts["destination"],
            treasureSplit=jatts["treasureSplit"],
            journeyEndorser=jatts["journeyEndorser"],
            firstName=ratts["requester"]["firstName"],
            lastName=ratts["requester"]["lastName"],
            nickname=ratts["requester"]["nickname"]
        )

        return data