import os
import json

from singer.catalog import Catalog, CatalogEntry, Schema

# from tap_zoom.endpoints import ENDPOINTS_CONFIG

SCHEMAS = {}
FIELD_METADATA = {}

def get_pk(stream_name, endpoints):
    for endpoint_stream_name, endpoint in endpoints.items():
        if stream_name == endpoint_stream_name:
            return endpoint['pk']

        if 'children' in endpoint:
            pk = get_pk(stream_name, endpoints=endpoint['children'])
            if pk:
                return pk

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

def get_schemas(endpoints):
    global SCHEMAS, FIELD_METADATA

    if SCHEMAS:
        return SCHEMAS, FIELD_METADATA

    schemas_path = get_abs_path('schemas')

    file_names = [f for f in os.listdir(schemas_path)
                  if os.path.isfile(os.path.join(schemas_path, f))]

    for file_name in file_names:
        stream_name = file_name[:-5]
        with open(os.path.join(schemas_path, file_name)) as data_file:
            schema = json.load(data_file)
            
        SCHEMAS[stream_name] = schema

        pk = get_pk(stream_name,endpoints=endpoints)

        if not pk: continue

        metadata = []
        metadata.append({
            'metadata': {
                'table-key-properties': pk
            },
            'breadcrumb': []
        })

        for prop, json_schema in schema['properties'].items():
            if prop in pk:
                inclusion = 'automatic'
            else:
                inclusion = 'available'
            metadata.append({
                'metadata': {
                    'inclusion': inclusion
                },
                'breadcrumb': ['properties', prop]
            })
        FIELD_METADATA[stream_name] = metadata

    return SCHEMAS, FIELD_METADATA

def discover(endpoints):
    schemas, field_metadata = get_schemas(endpoints)
    catalog = Catalog([])

    for stream_name, schema_dict in schemas.items():
        schema = Schema.from_dict(schema_dict)
        pk = get_pk(stream_name,endpoints=endpoints)
        if not pk:continue
        metadata = field_metadata[stream_name]

        catalog.streams.append(CatalogEntry(
            stream=stream_name,
            tap_stream_id=stream_name,
            key_properties=pk,
            schema=schema,
            metadata=metadata
        ))

    return catalog
