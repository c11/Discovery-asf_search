from asf_search.search.search import ASFProduct, ASFSearchResults
# from fixtures.baseline_search_fixtures import s1_search_response, s1_baseline_stack
from unittest.mock import patch

def run_test_ASFProduct_Geo_Search(geographic_response):
    product = ASFProduct(geographic_response)

    geojson = product.geojson()
    assert(geojson['geometry'] == geographic_response['geometry'])
    assert(geojson['properties'] == geographic_response['properties'])

def run_test_stack( reference, s1_baseline_stack):
    product = ASFProduct(reference)
    
    with patch('asf_search.baseline_search.search') as search_mock:
        search_mock.return_value = ASFSearchResults(map(lambda prod: ASFProduct(prod), s1_baseline_stack))
        stack = product.stack()
        
        assert(len(stack) == 4)
        for(idx, secondary) in enumerate(stack):
            assert(secondary.properties['temporalBaseline'] >= 0)
            
            if(idx > 0):
                assert(secondary.properties['temporalBaseline'] >= stack[idx].properties['temporalBaseline'])
