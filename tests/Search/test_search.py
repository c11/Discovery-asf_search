from numbers import Number
from asf_search import ASFSearchOptions
from asf_search.ASFProduct import ASFProduct
from asf_search.CMR.translate import get
from asf_search.constants import INTERNAL
from asf_search.exceptions import ASFSearchError
from asf_search.search import search
from asf_search.ASFSearchResults import ASFSearchResults
from asf_search.CMR import platform_datasets

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from pytest import raises

import requests_mock

def run_test_ASFSearchResults(search_resp):
    search_results = ASFSearchResults([ASFProduct(product) for product in search_resp])

    assert(len(search_results) == len(search_resp))
    assert(search_results.geojson()['type'] == 'FeatureCollection')

    for (idx, feature) in enumerate(search_results):
        # temporal and perpendicular baseline values are calculated post-search, 
        # so there's no instance where they'll be returned in a CMR search
        search_resp[idx]['properties'].pop('temporalBaseline', None)
        search_resp[idx]['properties'].pop('perpendicularBaseline', None)

        assert(feature.geojson()['geometry'] == search_resp[idx]['geometry'])
        for key, item in feature.geojson()['properties'].items():
            assert(item == search_resp[idx]['properties'][key])

def run_test_search(search_parameters, answer):
    with requests_mock.Mocker() as m:
        m.post(f"https://{INTERNAL.CMR_HOST}{INTERNAL.CMR_GRANULE_PATH}", json={'items': answer, 'hits': len(answer)})
        response = search(**search_parameters)

        if search_parameters.get("maxResults", False):
            assert(len(response) == search_parameters["maxResults"])

        assert(len(response) == len(answer))
        # assert(response.geojson()["features"] == answer)

def run_test_search_http_error(search_parameters, status_code: Number, report: str):
    
    if not len(search_parameters.keys()):
        with requests_mock.Mocker() as m:
            m.register_uri('POST', f"https://{INTERNAL.CMR_HOST}{INTERNAL.CMR_GRANULE_PATH}", status_code=status_code, json={'errors': {'report': report}})
            m.register_uri('POST', f"https://search-error-report.asf.alaska.edu/", real_http=True)
            searchOptions = ASFSearchOptions(**search_parameters)
            results = search(opts=searchOptions)
            assert len(results) == 0
            with raises(ASFSearchError):
                results.raise_if_incomplete()
            return

    # If we're not doing an empty search we want to fire off one real query to CMR, then interrupt it with an error
    # We can tell a search isn't the first one by checking if 'CMR-Search-After' has been set 
    def custom_matcher(request: requests.Request):
        if 'CMR-Search-After' in request.headers.keys():
            resp = requests.Response()
            resp.status_code = 200
            return resp
        return None

    with requests_mock.Mocker() as m:
        m.register_uri('POST', f"https://{INTERNAL.CMR_HOST}{INTERNAL.CMR_GRANULE_PATH}", real_http=True)
        m.register_uri('POST', f"https://{INTERNAL.CMR_HOST}{INTERNAL.CMR_GRANULE_PATH}", additional_matcher=custom_matcher, status_code=status_code, json={'errors': {'report': report}})
        m.register_uri('POST', f"https://search-error-report.asf.alaska.edu/", real_http=True)

        search_parameters['maxResults'] = INTERNAL.CMR_PAGE_SIZE + 1
        searchOptions = ASFSearchOptions(**search_parameters)
        results = search(opts=searchOptions)
        
        assert results is not None
        assert 0 < len(results) <= INTERNAL.CMR_PAGE_SIZE
        with raises(ASFSearchError):
            results.raise_if_incomplete()

@retry(
    reraise=True,
    wait=wait_fixed(3),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((requests.ReadTimeout, requests.HTTPError))
)
def test_datasets_search():
    datasets = ['SENTINEL-1', 'RADARSAT-1', 'UAVSAR']
    should_raise_error = len([dataset for dataset in datasets if not platform_datasets.get(dataset)]) > 0
    
    if should_raise_error:
        with raises(ValueError):
            search(datasets=datasets, maxResults=1)

    # get collection concept-ids from shortName cmr query
    else:
        valid_collections = []
        for dataset in datasets:
            valid_collections.extend(platform_datasets.get(dataset))
        
        response = search(datasets=datasets, maxResults=250)

        # Granules don't keep track of their collection concept-ids, 
        # but they do have the collection names we can use to find them!
        shortNames = '&'.join(list(set([f"shortName[]={get(product.umm, 'CollectionReference', 'ShortName')}" for product in response])))

        r = requests.get(f"https://cmr.earthdata.nasa.gov/search/collections.umm_json?{shortNames}&provider=ASF")
        r.raise_for_status()

        items = r.json()['items']
        concept_ids = [item['meta']['concept-id'] for item in items]

        # check that results are limited to the expected datasets
        for concept_id in concept_ids:
            assert concept_id in valid_collections
        