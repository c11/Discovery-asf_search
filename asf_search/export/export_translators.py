# from .count import count, req_fields_count
from asf_search import ASFSearchResults
from .csv import ASFSearchResults_to_csv, get_additional_csv_fields
from .kml import ASFSearchResults_to_kml, get_additional_kml_fields
from .metalink import get_additional_metalink_fields, ASFSearchResults_to_metalink
from types import FunctionType
from datetime import datetime
# from .download import cmr_to_download, req_fields_download
from .jsonlite import get_additional_jsonlite_fields, ASFSearchResults_to_jsonlite
from .jsonlite2 import ASFSearchResults_to_jsonlite2

def output_translators():
    return {
        'csv':          [results_to_format(get_additional_csv_fields, ASFSearchResults_to_csv), 'text/csv; charset=utf-8', 'csv'],
        'kml':          [results_to_format(get_additional_kml_fields, ASFSearchResults_to_kml), 'application/vnd.google-earth.kml+xml; charset=utf-8', 'kmz'],
        'metalink':     [results_to_format(get_additional_metalink_fields, ASFSearchResults_to_metalink), 'application/metalink+xml; charset=utf-8', 'metalink'],
        'jsonlite':     [results_to_format(get_additional_jsonlite_fields, ASFSearchResults_to_jsonlite), 'application/json; charset=utf-8', 'json'],
        'jsonlite2':     [results_to_format(get_additional_jsonlite_fields, ASFSearchResults_to_jsonlite2), 'application/json; charset=utf-8', 'json'],
    }

def results_to_format(get_additional_fields: FunctionType, to_export_format: FunctionType):
    return lambda results: to_export_format(get_properties_list(results, get_additional_fields))

def get_properties_list(results: ASFSearchResults, get_additional_fields):
    property_list = []
    
    for product in results:
        additional_fields = get_additional_fields(product)
        properties = {**product.properties, **additional_fields}
        property_list.append(properties)
    
    for product in property_list:
        for key, data in product.items():
            if 'date' in key.lower() or 'time' in key.lower():
                time = data[:-1] if data.endswith("Z") else data 
                time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%f')
                product[key] = time.strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    return property_list
