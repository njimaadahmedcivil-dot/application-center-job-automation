import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import job_search as s

def test_canonical_url_drops_trackers_but_not_job_ids():
    assert s.canonical_url('https://jobs.example.com/123/?utm_source=google&job=123&gclid=z')=='https://jobs.example.com/123?job=123'

def test_reject_senior_and_irrelevant_and_foreign():
    common={'company':'Example','job_url':'https://example.com/1','location':'Berlin, Germany'}
    assert not s.track_and_score({**common,'role':'Senior Director Construction','description':''})
    assert not s.track_and_score({**common,'role':'Chef de cuisine','description':''})
    assert not s.track_and_score({**common,'role':'Junior Bauleiter','location':'London, UK','description':''})

def test_find_and_dedup_across_feed_sources():
    jobs=[{'company':'Builder','role':'Junior Bauleiter','location':'Berlin','job_url':'https://jobs.example.org/1?utm_source=xxx','description':'German B2; Führerschein B'},
          {'company':'Builder','role':'Junior Bauleiter','location':'Berlin','job_url':'https://jobs.example.org/1','description':'repeat'},
          {'company':'Store','role':'Koch','location':'Berlin','job_url':'https://jobs.example.org/2'}]
    got=s.filter_jobs(jobs)
    assert len(got)==1
    assert got[0]['track']=='Civil engineering'
    assert 'German B2' in got[0]['notes']
    assert got[0]['status']=='discovered'

def test_respect_existing_sheet_rows():
    assert s.filter_jobs([{'company':'Builder','role':'Junior Bauleiter','location':'Berlin','job_url':'https://example.com/a'}],seen_urls={'https://example.com/a'})==[]

class MockResponse:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data

class MockGoogle:
    def __init__(self): self.posts=[]
    def get(self,*args,**kwargs): return MockResponse({'values':[s.HEADERS,['a','Builder','Junior Bauleiter','Civil engineering','Berlin','https://example.com/already']]})
    def post(self,url,params,json,timeout):
        self.posts.append((url,params,json))
        return MockResponse({'updates':{}})

def test_mock_google_append_and_existing_dedup():
    api=MockGoogle()
    urls,triples,n=s.read_existing(api,s.SHEET_ID)
    assert n==1
    jobs=s.filter_jobs([{'company':'Builder','role':'Junior Bauleiter','location':'Berlin','job_url':'https://example.com/already'}, {'company':'C','role':'Junior Bauleiter','location':'Hamburg','job_url':'https://example.com/new'}],urls,triples)
    assert len(jobs)==1
    assert s.append_jobs(api,s.SHEET_ID,jobs)==1
    row=api.posts[0][2]['values'][0]
    assert row[8]=='discovered' and row[10]=='' and row[11]==''
    assert row[5]=='https://example.com/new'

class FakeSearch:
    def get(self,url,**kwargs):
        return MockResponse({'data':[{'company_name':'Construct GmbH','title':'Junior Bauleiter','location':'Berlin','url':'https://construct.example/jobs/1','description':'Baukoordination'}],'links':{'next':None}})

def test_arbeitnow_parser_mock():
    jobs=list(s.collect_arbeitnow(FakeSearch(),pages=1))
    assert jobs[0]['company']=='Construct GmbH'
    assert s.filter_jobs(jobs)[0]['fit']>50

def test_role_profiles_can_turn_searches_on_and_off_without_python_edit():
    rows=[s.ROLE_HEADERS,['civil','FALSE','Civil engineering','Civil engineering','bauleiter;site engineer',''],
          ['teamlead','TRUE','Logistics Team Lead','Logistics & supply chain','teamleiter logistik;logistics team lead','']]
    profiles=s.parse_role_rows(rows)
    items=[{'company':'Builder','role':'Junior Bauleiter','location':'Berlin','job_url':'https://example.com/civil'},
           {'company':'Logistics Co','role':'Teamleiter Logistik','location':'Berlin','job_url':'https://example.com/lead'}]
    found=s.filter_jobs(items,profiles=profiles)
    assert len(found)==1 and found[0]['role']=='Teamleiter Logistik'
    rows[1][1]='TRUE'
    assert len(s.filter_jobs(items,profiles=s.parse_role_rows(rows)))==2

def test_profile_row_strict_headers_and_disabled_everything():
    try: s.parse_role_rows([['bad']]); assert False
    except ValueError: pass
    profiles=s.parse_role_rows([s.ROLE_HEADERS,['civil','FALSE','Civil','Civil engineering','bauleiter','']])
    assert s.filter_jobs([{'company':'B','role':'Bauleiter','location':'Berlin','job_url':'https://a.example/c'}],profiles=profiles)==[]

def test_profile_api_sheet_mock():
    class Sheet:
        def get(self,url,timeout):
            assert 'Role_Searches!A1:F200' in url
            return MockResponse({'values':[s.ROLE_HEADERS,['lead','TRUE','Logistics Team Lead','Logistics & supply chain','teamleiter logistik','']]})
    assert s.read_role_profiles(Sheet(),s.SHEET_ID)[0]['enabled']

class FakeLever:
    def get(self,url,**kwargs):
        return MockResponse([{'text':'Junior Bauingenieur','hostedUrl':'https://jobs.lever.co/demo/a','categories':{'location':'Berlin, Germany'},'descriptionPlain':'Construction'}])

def test_lever_parser_mock():
    jobs=list(s.collect_lever(FakeLever(),[{'site':'sample','company':'Sample GmbH'}]))
    assert jobs[0]['company']=='Sample GmbH' and jobs[0]['role']=='Junior Bauingenieur'

class FakeSmartRecruiters:
    def get(self,url,**kwargs):
        return MockResponse({'content':[{'id':'abc123','name':'Logistics Team Lead','location':{'city':'Berlin','country':'Germany'}}], 'totalFound':1})

def test_smartrecruiters_parser_mock():
    jobs=list(s.collect_smartrecruiters(FakeSmartRecruiters(),[{'company_id':'Sample','company':'Sample GmbH'}]))
    assert jobs[0]['role']=='Logistics Team Lead' and 'Berlin' in jobs[0]['location']

def test_source_catalog_has_honest_status():
    catalog=json.loads((Path(__file__).resolve().parents[1]/'config/source_catalog.json').read_text())
    assert len(catalog)>40
    assert next(x for x in catalog if x['name']=='XING')['integration_status']=='not_integrated'
    assert next(x for x in catalog if x['name']=='Arbeitnow')['integration_status']=='implemented'


def test_general_engineering_medical_false_positive_rejected():
    profiles=s.parse_role_rows([s.ROLE_HEADERS,['civil','TRUE','Civil','Civil engineering','projektingenieur;project engineer','']])
    vals=[{'company':'Medico','role':'Projektingenieur in der Medizintechnik','location':'Berlin','job_url':'https://medico.example/1','description':'Product development of medical devices'},
          {'company':'Bau','role':'Projektingenieur Hochbau','location':'Berlin','job_url':'https://bau.example/2','description':'Construction site coordination'}]
    assert [x['company'] for x in s.filter_jobs(vals,profiles=profiles)]==['Bau']


class AshbySession:
    def get(self,url,**kwargs):
        return MockResponse({'jobs':[{'isListed':True,'title':'Junior Bauleiter','location':'Berlin, Germany','jobUrl':'https://jobs.ashbyhq.com/example/one','descriptionPlain':'Construction'}]})


def test_ashby_mock():
    jobs=list(s.collect_ashby(AshbySession(),[{'board':'example','company':'TestCo'}]))
    assert jobs[0]['company']=='TestCo' and jobs[0]['role']=='Junior Bauleiter'


class RecruiteeSession:
    def get(self,url,**kwargs):
        return MockResponse({'offers':[{'title':'Teamleiter Logistik','city':'Berlin','careers_url':'https://example.recruitee.com/o/logistik','description':'Warehouse shift staffing'}]})


def test_recruitee_mock():
    jobs=list(s.collect_recruitee(RecruiteeSession(),[{'site':'example','company':'Example'}]))
    assert jobs[0]['role']=='Teamleiter Logistik'


class WorkableSession:
    def get(self,url,**kwargs):
        return MockResponse({'jobs':[{'title':'Junior Bauingenieur','location':{'city':'Berlin','country':'Germany'},'url':'https://apply.workable.com/sample/j/123/'}]})


def test_workable_mock():
    jobs=list(s.collect_workable(WorkableSession(),[{'account':'sample','company':'Sample'}]))
    assert jobs[0]['role']=='Junior Bauingenieur' and 'Germany' in jobs[0]['location']


class PersonioSession:
    def get(self,url,**kwargs):
        class R:
            content=b'<positions><position><id>100</id><name>Bauleiter</name><city>Berlin</city><country>Germany</country><jobDescription>Baustelle</jobDescription></position></positions>'
            def raise_for_status(self):pass
        return R()


def test_personio_mock():
    jobs=list(s.collect_personio(PersonioSession(),[{'tenant':'sample','company':'Company'}]))
    assert jobs[0]['role']=='Bauleiter' and 'Berlin' in jobs[0]['location']


def test_run_history_appends_only_summary():
    class HistoryClient:
        def __init__(self): self.writes=[]
        def post(self,url,params,json,timeout):
            self.writes.append((url,json['values'][0]))
            return MockResponse({'updates':{}})
    fake=HistoryClient()
    profiles=[{'name':'Civil engineering','enabled':True},
              {'name':'Other','enabled':False}]
    s.append_run_history(fake,s.SHEET_ID,120,4,3,profiles,[('Arbeitnow',120,'ok')])
    assert len(fake.writes)==1
    url, row=fake.writes[0]
    assert 'Run_History' in url
    assert row[1:4]==[120,4,3]
    assert row[4]=='Civil engineering'


def test_ba_jobs_parse_official_link_and_keep_german_location():
    class BASession:
        def get(self,url,params,headers,timeout):
            assert '/pc/v6/jobs' in url
            assert params['was']=='bauleiter'
            assert headers['X-API-Key']=='jobboerse-jobsuche'
            return MockResponse({'stellenangebote':[{
                'refnr':'10000-12345678-S','titel':'Bauleiter Hochbau',
                'arbeitgeber':'Bau GmbH','arbeitsort':{'ort':'Berlin','land':'Deutschland'}}]})
    profiles=[{'enabled':True,'terms':['bauleiter'],'name':'Civil','track':'Civil engineering'}]
    results=list(s.collect_ba_jobs(BASession(),profiles,{'max_queries':2,'results_per_query':10,'days':7}))
    assert len(results)==1
    assert results[0]['job_url']=='https://www.arbeitsagentur.de/jobsuche/jobdetail/10000-12345678-S'
    assert results[0]['location']=='Berlin, Deutschland'


def test_ba_rejects_unexpected_payload():
    class BadResponse:
        def raise_for_status(self): pass
        def json(self): return {'not_jobs':[]}
    class BadSession:
        def get(self, *args, **kwargs): return BadResponse()
    profiles=[{'enabled':True,'terms':['bauleiter'],'name':'Civil','track':'Civil engineering'}]
    import pytest
    with pytest.raises(ValueError):
        list(s.collect_ba_jobs(BadSession(),profiles,{}))


def test_adzuna_requires_secrets_and_never_embeds_them(monkeypatch):
    monkeypatch.delenv('ADZUNA_APP_ID',raising=False)
    monkeypatch.delenv('ADZUNA_APP_KEY',raising=False)
    class NoNetwork:
        def get(self,*args,**kwargs): raise AssertionError('No API call without credentials')
    assert list(s.collect_adzuna(NoNetwork(),[{'enabled':True,'terms':['bauleiter']}],{}))==[]


def test_adzuna_parsing_with_fake_session(monkeypatch):
    monkeypatch.setenv('ADZUNA_APP_ID','FAKE_ID')
    monkeypatch.setenv('ADZUNA_APP_KEY','FAKE_KEY')
    class AdzunaSession:
        def get(self,url,params,timeout):
            assert '/jobs/de/search/' in url
            assert params['what']=='bauleiter'
            return MockResponse({'results':[{'title':'Bauleiter Hochbau','redirect_url':'https://example.com/job/1',
                'company':{'display_name':'Example GmbH'},'location':{'display_name':'Hamburg, Deutschland'},
                'description':'Hochbau'}]})
    rows=list(s.collect_adzuna(AdzunaSession(),[{'enabled':True,'terms':['bauleiter']}],{'max_queries':1}))
    assert rows[0]['company']=='Example GmbH'
    assert rows[0]['source']=='Adzuna Germany official API'


def test_search_queries_rotate_across_active_categories():
    profiles=[
      {'enabled':True,'terms':['bauleiter','bauingenieur','arbeitsvorbereitung']},
      {'enabled':True,'terms':['teamleiter logistik','lagerleitung']},
      {'enabled':False,'terms':['unwanted term']}
    ]
    assert s.active_search_terms(profiles,4)==['bauleiter','teamleiter logistik','bauingenieur','lagerleitung']
