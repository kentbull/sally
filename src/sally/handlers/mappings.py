# -*- encoding: utf-8 -*-
"""
SALLY
sally.core.handling.mapping module

Mapping credential names to schema SAIDs to simplify lookup and use human-friendly names in code
"""
from collections import namedtuple

from keri import kering

SchemaMapping = namedtuple('CredentialMapping', 'credential_type said')


def resolve_said_to_type(mappings, schema_said):
    for mapping in mappings:
        if mapping.said == schema_said:
            return mapping.credential_type
    raise kering.ValidationError(f"no mapping found for schema {schema_said}")

def resolve_type_to_said(mappings, credential_type):
    for mapping in mappings:
        if mapping.credential_type == credential_type:
            return mapping.said
    raise kering.ValidationError(f"no mapping found for schema {credential_type}")