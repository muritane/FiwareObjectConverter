#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Converts an NGSI v2 Normalized Representation
into an NGSI-LD Representation
Copyright (c) 2018 FIWARE Foundation e.V.
Author: José Manuel Cantera
"""


from rfc3987 import parse
etsi_core_context = 'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'


class LD_Normalizer:
    @classmethod
    def _ngsild_uri(cls, type_part, id_part):
        template = 'urn:ngsi-ld:{}:{}'
        return template.format(type_part, id_part)

    # Generates an Entity Id as a URI
    @classmethod
    def _ld_id(cls, entity_id, entity_type):
        print("_ld_id")
        print("entity_id: ", entity_id)
        print("entity_type: ", entity_type)
        out = entity_id
        try:
            d = parse(str(entity_id), rule='URI')
            scheme = d['scheme']
            print("d: ", d)
            print("scheme: ", scheme)
            if scheme not in ('urn', 'http', 'https'):
                print("scheme not in ('urn', 'http', 'https')")
                raise ValueError
        except ValueError:
            print("except ValueError")
            out = cls._ngsild_uri(entity_type, entity_id)

        print("out: ", out)
        return out

    # Generates a Relationship's object as a URI
    @classmethod
    def _ld_object(cls, attribute_name, entity_id):
        out = entity_id
        try:
            d = parse(str(entity_id), rule='URI')
            scheme = d['scheme']
            if scheme not in ('urn', 'http', 'https'):
                raise ValueError
        except ValueError:
            entity_type = ''
            if attribute_name.startswith('ref'):
                entity_type = attribute_name[3:]

            out = cls._ngsild_uri(entity_type, entity_id)

        return out

    # Do all the transformation work
    @classmethod
    def _normalized_to_ld(cls, entity, ld_context_uri):
        if not ld_context_uri is None:
            out = {
                '@context': [ld_context_uri, etsi_core_context]
            }
        else:
            out = {
                '@context': [etsi_core_context]
            }

        for key in entity:
            if key == 'id':
                print("_normalized_to_ld if key == 'id'")
                out[key] = cls._ld_id(entity['id'], entity['type'])
                continue

            if key == 'type':
                out[key] = entity[key]
                continue

            if key == 'dateCreated':
                out['createdAt'] = cls._normalize_date(entity[key]['value'])
                continue

            if key == 'dateModified':
                out['modifiedAt'] = cls._normalize_date(entity[key]['value'])
                continue

            attr = entity[key]
            out[key] = cls._normalize_attribute(key, attr)
        return out

    @classmethod
    def _normalize_attribute(cls, key, attr):
        ld_attr = {}
        if not('type' in attr) or attr['type'] != 'Relationship':
            ld_attr['type'] = 'Property'
            if attr['type'] in ['string', 'number', 'boolean']:
                ld_attr['value'] = attr['value']
            elif attr['type'] == 'array':
                ld_attr['value'] = []
                obj_attr = attr['value']
                for new_key in obj_attr:
                    ld_attr['value'].append(
                        cls._normalize_attribute(None, new_key))
            else:
                ld_attr['value'] = {}
                obj_attr = attr['value']
                for new_key in obj_attr:
                    ld_attr['value'][new_key] = cls._normalize_attribute(
                        new_key, obj_attr[new_key])
                ld_attr['value']['type'] = attr['type']
        else:
            ld_attr['type'] = 'Relationship'
            aux_obj = attr['value']
            if isinstance(aux_obj, list):
                ld_attr['object'] = list()
                for obj in aux_obj:
                    ld_attr['object'].append(cls._ld_object(key, obj))
            else:
                ld_attr['object'] = cls._ld_object(key, str(aux_obj))

        # if key == 'location':
        #    ld_attr['type'] = 'GeoProperty'
        #
        # if 'type' in attr and attr['type'] == 'DateTime':
        #    ld_attr['value'] = {
        #        '@type': 'DateTime',
        #        '@value': cls._normalize_date(attr['value'])
        #    }
        #
        # if 'type' in attr and attr['type'] == 'PostalAddress':
        #    ld_attr['value']['type'] = 'PostalAddress'

        if 'metadata' in attr:
            metadata = attr['metadata']

            for mkey in metadata:
                if mkey == 'timestamp':
                    ld_attr['observedAt'] = cls._normalize_date(
                        metadata[mkey]['value'])
                elif mkey == 'unitCode':
                    ld_attr['unitCode'] = metadata[mkey]['value']
                else:
                    sub_attr = dict()
                    # Metadata which are Relationships is assumed not to be there
                    sub_attr['type'] = 'Property'
                    sub_attr['value'] = metadata[mkey]['value']
                    ld_attr[mkey] = sub_attr
        return ld_attr

    @classmethod
    def _normalize_date(cls, date_str):
        out = date_str

        if not date_str.endswith('Z'):
            out += 'Z'

        return out

    @classmethod
    def normalize(cls, input_, context_=None):
        result = cls._normalized_to_ld(input_, context_)
        return result