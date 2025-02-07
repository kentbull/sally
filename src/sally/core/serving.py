# -*- encoding: utf-8 -*-
"""
SALLY
sally.core.serving module

Endpoint service
"""
import os

import falcon
from base64 import urlsafe_b64encode as encodeB64

from hio.base import doing
from hio.core import http
from hio.help import decking
from keri import help
from keri.app import indirecting, storing, notifying
from keri.core import eventing, parsing, routing
from keri.app.cli.commands import incept
from keri.core import routing, eventing
from keri.end import ending
from keri.peer import exchanging
from keri.vdr import viring, verifying
from keri.vdr.eventing import Tevery
from keri.vc import protocoling

from sally.core import handling, basing
from sally.core import handling, basing, monitoring, httping
from sally.core.credentials import TeveryCuery
from sally.core.monitoring import HealthEnd

logger = help.ogler.getLogger()

def setup(hby, *, alias, httpPort, hook, auth, timeout=10, retry=3, incept_args=None):
    """
    Setup components, HTTP endpoints, and MailboxDirector working with witnesses to receive events.

    Parameters:
        hby (Habery): identifier database environment
        alias (str): alias of the identifier representing this agent
        httpPort (int): external port to listen on for HTTP messages
        hook (str): URL of external web hook to notify of credential issuance and revocations
        auth (str): alias or AID of external authority for contacts and credentials
        timeout (int): escrow timeout (in minutes) for events not delivered to upstream web hook
        retry (int): retry delay (in seconds) for failed web hook attempts
        incept_args (dict): arguments for incepting Sally's identifier if it does not exist
    """
    host = "0.0.0.0"
    cues = decking.Deck()
    # make hab
    if incept_args is None:
        incept_args = {}
    hab = hby.habByName(name=alias)
    if hab is None:
        if incept_args["incept_file"] is None:
            raise ValueError("incept file by arg --incept-file is required to create a new identifier")
        logger.info(f"Making new hab {alias} in Habery {incept_args.get('name', '')}")
        hab = hby.makeHab(name=alias, **inception_config(**incept_args))
    else:
        logger.info(f"Hab '{alias}' already exists, using...")

    logger.info(f"Using hab {hab.name}:{hab.pre}")
    logger.info(f"\tCESR Qualifed Base64 Public Key:  {hab.kever.serder.verfers[0].qb64}")
    logger.info(f"\tPlain Base64 Public Key:          {encodeB64(hab.kever.serder.verfers[0].raw).decode('utf-8')}")

    # HTTP Server
    app = falcon.App(middleware=httping.cors_middleware())
    server = http.Server(port=httpPort, app=app)
    httpServerDoer = http.ServerDoer(server=server)

    # KEL, ACDC, exchange message, and reply message components
    reger = viring.Reger(name=hab.name, db=hab.db, temp=False)
    verifier = verifying.Verifier(hby=hby, reger=reger)

    mbx = storing.Mailboxer(name=hby.name)
    exc = exchanging.Exchanger(hby=hby, handlers=[])
    rep = storing.Respondant(hby=hby, mbx=mbx)

    cdb = basing.CueBaser(name=hby.name)
    clear_escrows(cdb)

    rvy = routing.Revery(db=hby.db)
    notifier = notifying.Notifier(hby=hby)
    # writes notifications for received IPEX grant exn messages
    protocoling.loadHandlers(hby=hby, exc=exc, notifier=notifier)

    kvy = eventing.Kevery(db=hby.db, lax=True, local=False, rvy=rvy)
    kvy.registerReplyRoutes(router=rvy.rtr)

    tvy = Tevery(reger=verifier.reger, db=hby.db, local=False)
    tvy.registerReplyRoutes(router=rvy.rtr)
    tc = TeveryCuery(cdb=cdb, reger=reger, cues=tvy.cues)

    parser = parsing.Parser(framed=True, kvy=kvy, tvy=tvy, rvy=rvy, vry=verifier, exc=exc)

    comms = handling.Communicator(hby=hby, hab=hab, cdb=cdb, reger=reger,
                                  auth=auth, hook=hook, timeout=timeout, retry=retry)
    app.add_route("/health", monitoring.HealthEnd(cdb=cdb))

    ending.loadEnds(app, hby=hby, default=hab.pre)

    rep = storing.Respondant(hby=hby, mbx=mbx)
    mbd = indirecting.MailboxDirector(
        hby=hby, exc=exc, kvy=kvy, tvy=tvy, rvy=rvy, verifier=verifier, rep=rep,
        topics=["/receipt", "/replay", "/multisig", "/credential", "/delegate", "/challenge"])  # topics to listen for messages on

    doers = [httpServerDoer, comms, tc]
    if listen:
        logger.info("Adding direct mode HTTP listener")
        # reading notifications for received ipex grant exn messages
        doers.extend(handling.loadHandlers(cdb=cdb, hby=hby, notifier=notifier, parser=parser))

        # Set up HTTP endpoint for PUT-ing application/cesr streams to the SallyAgent at '/'
        httpEnd = indirecting.HttpEnd(rxbs=parser.ims, mbx=mbx)
        app.add_route('/', httpEnd)
        sallyAgent = SallyAgent(hab=hab, parser=parser, kvy=kvy, tvy=tvy, rvy=rvy, exc=exc, cues=cues)
        doers.append(sallyAgent)
    else:
        logger.info("Adding indirect mode mailbox listener")
        mbd = indirecting.MailboxDirector(hby=hby,
                                          exc=exc,
                                          kvy=kvy,
                                          tvy=tvy,
                                          rvy=rvy,
                                          verifier=verifier,
                                          rep=rep,
                                          topics=["/receipt", "/replay", "/multisig", "/credential", "/delegate",
                                                  "/challenge"])

    return doers


def clear_escrows(cdb):
    """Clear escrows if the environment variable CLEAR_ESCROWS is set to True."""
    if env_var_to_bool("CLEAR_ESCROWS", True):
        logger.info("Clearing escrows")
        cdb.clearEscrows()


def env_var_to_bool(var_name, default=False):
    """Convert an environment variable to a boolean value."""
    val = os.getenv(var_name, default)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ["true", "1"]
    return default

def inception_config(name=None, base=None, alias=None, bran=None, incept_file=None, config_dir=None):
    """
    Inception configuration for Sally's identifier prefix.
    Returns a dict of inception arguments for Sally's identifier prefix.

    This uses an object so that it can be merged with the incept file configuration like the
    multicommand args object by using object properties rather than dictionary keys, which is what
    incept.mergeArgsWithFile expects.
    """
    class Object(object):
        pass
    icp_args = Object()
    icp_args.name = name
    icp_args.base = base
    icp_args.alias = alias
    icp_args.bran = bran
    icp_args.file = incept_file if config_dir is None else os.path.join(config_dir, incept_file)
    icp_args.transferable = True
    icp_args.icount = None
    icp_args.wits = []
    icp_args.toad = None
    icp_args.isith = None
    icp_args.ncount = None
    icp_args.nsith = None
    icp_args.delpre = None
    icp_args.est_only = False
    icp_args.data = None
    return incept.mergeArgsWithFile(icp_args).__dict__

class SallyAgent(doing.DoDoer):
    """
    Agent Doer for running the Sally service in direct HTTP mode rather than indirect mode.

    Direct mode is used when presenting directly to Sally after resolving Sally as a Controller OOBI.
    Indirect mode is used when presenting to Sally via a mailbox whether from a witness or a mailbox agent.
    """

    def __init__(self, hab, parser, kvy, tvy, rvy, exc, cues=None, **opts):
        """
        Initializes the SallyAgent with the Sally identifier (Hab), parser, KEL, TEL, and Exchange message processor
        so that it can process incoming credential presentations.
        """
        self.hab = hab
        self.parser = parser
        self.kvy = kvy
        self.tvy = tvy
        self.rvy = rvy
        self.exc = exc
        self.cues = cues if cues is not None else decking.Deck()
        doers = [doing.doify(self.msgDo), doing.doify(self.escrowDo)]
        super().__init__(doers=doers, **opts)

    def msgDo(self, tymth=None, tock=0.0):
        """
        Processes incoming messages from the parser which triggers the KEL, TEL, Router, and Exchange
        message processor to process credential presentations.
        """
        self.wind(tymth)
        self.tock = tock
        _ = (yield self.tock)

        if self.parser.ims:
            logger.debug(f"Sally received:\n%s\n...\n", self.parser.ims[:1024])
        done = yield from self.parser.parsator(local=True)
        return done

    def escrowDo(self, tymth=None, tock=0.0):
        """
        Processes KEL, TEL, Router, and Exchange message processor escrows.
        This ensures that each component processes the messages parsed from the HttpEnd.
        """
        self.wind(tymth)
        self.tock = tock
        _ = (yield self.tock)

        while True:
            self.kvy.processEscrows()
            self.rvy.processEscrowReply()
            if self.tvy is not None:
                self.tvy.processEscrows()
            self.exc.processEscrow()

            yield