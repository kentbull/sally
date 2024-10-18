# -*- encoding: utf-8 -*-
"""
SALLY
sally.core.handling module

EXN Message handling
"""
import datetime
import json
from base64 import urlsafe_b64encode as encodeB64
from urllib import parse

from hio.base import doing
from hio.core import http
from hio.help import Hict
from keri import help, kering
from keri.core import coring
from keri.core.serdering import SerderACDC
from keri.end import ending
from keri.help import helping
from keri.peer import exchanging

from sally.core import httping
from sally.handlers import abydos, vlei, mappings
from sally.handlers.abydos import JOURNEY_TYPE, REQUEST_TYPE, MARK_TYPE, CHARTER_TYPE
from sally.handlers.mappings import SchemaMapping

logger = help.ogler.getLogger()

def loadHandlers(cdb, hby, notifier, parser):
    """ Load handlers for the peer-to-peer challenge response protocol

    Parameters:
        cdb (CueBaser): communication escrow database environment
        notifier (Notifier): Notifications
        parser (Parser)

    """
    return [PresentationProofHandler(cdb=cdb, hby=hby, notifier=notifier, parser=parser)]


class PresentationProofHandler(doing.Doer):
    """ Processor for responding to presentation proof peer to peer message.

      The payload of the message is expected to have the following format:

    """

    def __init__(self, cdb, hby, notifier, parser, **kwa):
        """ Initialize instance

        Parameters:
            cdb (CueBaser): communication escrow database environment
            notifier(Notifier): to read notifications to processes exns
            **kwa (dict): keyword arguments passes to super Doer

        """
        self.cdb = cdb
        self.hby = hby
        self.notifier = notifier
        self.parser = parser
        super(PresentationProofHandler, self).__init__()

    def recur(self, tyme):
        """ Handle incoming messages by queueing presentation messages to be handled when credential is received

        Parameters:
            tymth (function): injected function wrapper closure returned by .tymen() of
                Tymist instance. Calling tymth() returns associated Tymist .tyme.
        """
        for keys, notice in self.notifier.noter.notes.getItemIter():
            logger.info(f"Processing notice {notice}")
            attrs = notice.attrs
            route = attrs['r']

            if route == '/exn/ipex/grant':
                # said of grant message
                said = attrs['d']
                exn, pathed = exchanging.cloneMessage(self.hby, said=said)
                embeds = exn.ked['e']

                for label in ("anc", "iss", "acdc"):
                    ked = embeds[label]
                    sadder = coring.Sadder(ked=ked)
                    ims = bytearray(sadder.raw) + pathed[label]
                    self.parser.parseOne(ims=ims)

                acdc = embeds["acdc"]
                said = acdc['d']

                sender = acdc['i']
                prefixer = coring.Prefixer(qb64=sender)

                self.cdb.snd.pin(keys=(said,), val=prefixer)
                self.cdb.iss.pin(keys=(said,), val=coring.Dater())

            # deleting wether its a grant or not, since we only process grant
            self.notifier.noter.notes.rem(keys=keys)

        return False


class Communicator(doing.DoDoer):
    """
    Communicator is responsible for communicating the receipt and successful verification
    of credential presentation and revocation messages from external third parties via
    web hook API calls.
    """

    def __init__(self, hby, hab, cdb, reger, auth, hook, timeout=10, retry=3.0, schema_mappings=None):
        """

        Create a communicator capable of persistent processing of messages and performing
        web hook calls.

        Parameters:
            hby (Habery): identifier database environment
            hab (Hab): identifier environment of this Communicator.  Used to sign hook calls
            cdb (CueBaser): communication escrow database environment
            reger (Reger): credential registry and database
            auth (str): AID of external authority for contacts and credentials
            hook (str): web hook to call in response to presentations and revocations
            timeout (int): escrow timeout (in minutes) for events not delivered to upstream web hook
            retry (float): retry delay (in seconds) for failed web hook attempts

        """
        if schema_mappings is None:
            schema_mappings = []
        self.hby = hby
        self.hab = hab
        self.cdb = cdb
        self.reger = reger
        self.hook = hook
        self.auth = auth
        self.timeout = timeout
        self.retry = retry
        self.clients = dict()
        self.schema_mappings: list[SchemaMapping] = schema_mappings
        for mapping in self.schema_mappings:
            logger.info(f'Configured mapping of | {mapping.said} | {mapping.credential_type}')
        self.vlei_handler = vlei.VLEIHandler(schema_mappings, reger, auth)
        self.abydos_handler = abydos.AbydosHandler(schema_mappings, reger, auth)
        self.schema_handlers: dict = {
            JOURNEY_TYPE: self.abydos_handler.validateJourney,
            REQUEST_TYPE: self.abydos_handler.validateJourneyMarkRequest,
            MARK_TYPE: self.abydos_handler.validateJourneyMark,
            CHARTER_TYPE: self.abydos_handler.validateJourneyCharter
        }
        self.payload_handlers: dict = {
            JOURNEY_TYPE: self.abydos_handler.treasureHuntingJourneyPayload,
            REQUEST_TYPE: self.abydos_handler.journeyMarkRequestPayload,
            MARK_TYPE: self.abydos_handler.journeyMarkPayload,
            CHARTER_TYPE: self.abydos_handler.journeyCharterPayload
        }

        super(Communicator, self).__init__(doers=[doing.doify(self.escrowDo)])

    def processPresentations(self):

        for (said,), dater in self.cdb.iss.getItemIter():
            # cancel presentations that have been around longer than timeout
            now = helping.nowUTC()
            logger.info(f"looking for credential {said}")
            if now - dater.datetime > datetime.timedelta(minutes=self.timeout):
                self.cdb.iss.rem(keys=(said,))
                continue

            if self.reger.saved.get(keys=(said,)) is not None:
                creder: SerderACDC = self.reger.creds.get(keys=(said,))
                try:
                    regk = creder.regi
                    state = self.reger.tevers[regk].vcState(creder.said)
                    if state is None or state.et not in (coring.Ilks.iss, coring.Ilks.bis):
                        self.cdb.recv.pin(keys=(said, dater.qb64), val=creder) # save revoked credential so we can remember it was presented already
                        raise kering.InvalidCredentialStateError(f"$evoked credential {creder.said} being presented")

                    handler_type = mappings.resolve_said_to_type(self.schema_mappings, creder.schema)
                    if handler_type in self.schema_handlers.keys():
                        handler = self.schema_handlers[handler_type]
                        handler(creder)
                    else:
                        raise kering.ValidationError(f"credential {creder.said} is of unsupported schema"
                                                     f" {creder.schema} from issuer {creder.issuer}")
                except kering.InvalidCredentialStateError as ex:
                    logger.error(ex)
                    logger.error(
                        f'Revoked credential {creder.said} from issuer {creder.issuer} being presented.')
                except kering.ValidationError as ex:
                    logger.error(f"credential {creder.said} from issuer {creder.issuer} failed validation: {ex}")
                else:
                    self.cdb.recv.pin(keys=(said, dater.qb64), val=creder)
                finally:
                    self.cdb.iss.rem(keys=(said,))

    def processRevocations(self):

        for (said,), dater in self.cdb.rev.getItemIter():

            # cancel revocations that have been around longer than timeout
            now = helping.nowUTC()
            if now - dater.datetime > datetime.timedelta(minutes=self.timeout):
                self.cdb.rev.rem(keys=(said,))
                continue

            creder = self.reger.creds.get(keys=(said,))
            if creder is None:  # received revocation before credential.  probably an error but let it timeout
                continue

            regk = creder.regi
            state = self.reger.tevers[regk].vcState(creder.said)
            if state is None:  # received revocation before status.  probably an error but let it timeout
                continue

            elif state.et in (coring.Ilks.iss, coring.Ilks.bis):  # haven't received revocation event yet
                continue

            elif state.et in (coring.Ilks.rev, coring.Ilks.brv):  # revoked
                self.cdb.rev.rem(keys=(said,))
                self.cdb.revk.pin(keys=(said, dater.qb64), val=creder)

    def processReceived(self, db, action):

        for (said, dates), creder in db.getItemIter():
            if said not in self.clients:
                resource = creder.schema
                actor = creder.issuer
                if action == "iss":  # presentation of issued credential
                    handler_type = mappings.resolve_said_to_type(self.schema_mappings, creder.schema)
                    if handler_type in self.payload_handlers.keys():
                        handler = self.payload_handlers[handler_type]
                        data = handler(creder, self.reger)
                    else:
                        logger.error(f"invalid credential with schema {creder.schema} said {creder.said} issuer {creder.issuer}")
                        raise kering.ValidationError(
                            f"credential {creder.said} is of unsupported schema"
                            f" {creder.schema} from issuer {creder.issuer}")
                else:  # revocation of credential
                    data = self.revokePayload(creder)

                self.request(creder.said, resource, action, actor, data)
                continue

            (client, clientDoer) = self.clients[said]
            if client.responses:
                response = client.responses.popleft()
                self.remove([clientDoer])
                client.close()
                del self.clients[said]

                if 200 <= response["status"] < 300:
                    db.rem(keys=(said, dates))
                    self.cdb.ack.pin(keys=(said,), val=creder)
                else:
                    dater = coring.Dater(qb64=dates)
                    now = helping.nowUTC()
                    if now - dater.datetime > datetime.timedelta(minutes=self.timeout):
                        db.rem(keys=(said, dates))

    def processAcks(self):
        for (said,), creder in self.cdb.ack.getItemIter():
            # TODO: generate EXN ack message with credential information
            logger.info(f"ACK for credential {said} will be sent to {creder.issuer}")
            self.cdb.ack.rem(keys=(said,))

    def escrowDo(self, tymth, tock=1.0):
        """ Process escrows of comms pipeline

        Steps involve:
           1. Sending local event with sig to other participants
           2. Waiting for signature threshold to be met.
           3. If elected and delegated identifier, send complete event to delegator
           4. If delegated, wait for delegator's anchor
           5. If elected, send event to witnesses and collect receipts.
           6. Otherwise, wait for fully receipted event

        Parameters:
            tymth (function): injected function wrapper closure returned by .tymen() of
                Tymist instance. Calling tymth() returns associated Tymist .tyme.
            tock (float): injected initial tock value.  Default to 1.0 to slow down processing

        """
        # enter context
        self.wind(tymth)
        self.tock = tock
        _ = (yield self.tock)

        while True:
            try:
                self.processEscrows()
            except Exception as e:
                logger.error(e)

            yield self.retry

    def processEscrows(self):
        """
        Process communication pipelines

        """
        self.processPresentations()
        self.processRevocations()
        self.processReceived(db=self.cdb.recv, action="iss")
        self.processReceived(db=self.cdb.revk, action="rev")
        self.processAcks()

    def request(self, said, resource, action, actor, data):
        """ Generate and launch request to remote hook

        Parameters:
            said (str): qb64 SAID of credential
            data (dict): serializable body to send with call
            action (str): the action performed on he resource [iss|rev]
            actor (str): qualified b64 AID of sender of the event
            resource (str): the resource type that triggered the event

        """
        purl = parse.urlparse(self.hook)
        client = http.clienting.Client(hostname=purl.hostname, port=purl.port)
        clientDoer = http.clienting.ClientDoer(client=client)
        self.extend([clientDoer])

        body = dict(
            action=action,
            actor=actor,
            data=data
        )

        raw = json.dumps(body).encode("utf-8")
        headers = Hict([
            ("Content-Type", "application/json"),
            ("Content-Length", len(raw)),
            ("Connection", "close"),
            ("Sally-Resource", resource),
            ("Sally-Timestamp", helping.nowIso8601()),
        ])
        path = purl.path or "/"

        keyid = encodeB64(self.hab.kever.serder.verfers[0].raw).decode('utf-8')
        header, unq = httping.siginput(self.hab, "sig0", "POST", path, headers, fields=["Sally-Resource", "@method",
                                                                                        "@path",
                                                                                        "Sally-Timestamp"],
                                       alg="ed25519", keyid=keyid)

        headers.extend(header)
        signage = ending.Signage(markers=dict(sig0=unq), indexed=True, signer=self.hab.pre, ordinal=None, digest=None,
                                 kind=None)

        headers.extend(ending.signature([signage]))

        client.request(
            method='POST',
            path=path,
            qargs=parse.parse_qs(purl.query),
            headers=headers,
            body=raw
        )

        self.clients[said] = (client, clientDoer)

    def revokePayload(self, creder):
        regk = creder.regi
        state = self.reger.tevers[regk].vcState(creder.said)

        data = dict(
            schema=creder.schema,
            credential=creder.said,
            revocationTimestamp=state.dt
        )

        return data


