"""Application Center job discovery -> Google Sheets, minimal dependencies.

Sources: public Arbeitnow API; optional explicitly configured RSS and Greenhouse API boards.
Other portal names are research targets, not native scraping integrations.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from html import unescape
import json
import logging
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from zoneinfo import ZoneInfo
import requests
import xml.etree.ElementTree as ET

SHEET_ID = '1JUKnCUmshWZpKV8-VOebJ-KNScMu9R45pf0j_crsD4w'
HEADERS = ['id','company','role','track','location','job_url','language','fit','status','discovered_at','applied_at','follow_up_at','interview_at','deadline','source','recruiter','cv_file','cover_letter_file','notes','updated_at']
CIVIL = re.compile(r'bauingenieur|bauleiter|bauüberwachung|bauleitung|construction|site engineer|baustelle|arbeitsvorbereitung|infrastruktur|civil engineer|terminplanung|projekt.*bau|hochbau|tiefbau|bauprojekt|construction management', re.I)
LOGISTICS = re.compile(r'logistik|logistics|supply chain|einkauf|procurement|buyer|materialdisponent|disponent|personalplanung|einsatzplanung|expedit|operations coordinator|projektkoordinator', re.I)
JUNIOR = re.compile(r'junior|graduate|entry.level|berufseinsteiger|nachwuchs|trainee|assistant|assistenz|associate|projektkoordinator|project engineer|projektingenieur',re.I)
SENIOR = re.compile(r'\b(senior|director|head of|leiter.*abteilung|principal|vp|vice president)\b',re.I)
GERMANY = re.compile(r'germany|deutschland|berlin|hamburg|frankfurt|münchen|munich|köln|cologne|essen|düsseldorf|stuttgart|leipzig|hannover|bremen|dortmund|bonn|karlsruhe|dresden|potsdam|augsburg|nürnberg|nuremberg|remote',re.I)
LOG = logging.getLogger('application_center')


def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', unescape(str(s or '')))).strip()


def canonical_url(url):
    """Keep the actual destination; remove only tracking query parameters."""
    x=urlsplit(str(url).strip())
    if x.scheme not in ('http','https') or not x.netloc: return ''
    q=[(k,v) for k,v in parse_qsl(x.query,keep_blank_values=True) if not (k.lower().startswith('utm_') or k.lower() in ('ref','source','fbclid','gclid'))]
    return urlunsplit((x.scheme.lower(),x.netloc.lower(),x.path.rstrip('/') or '/',urlencode(q),'') )


def normalize(raw):
    item={k:clean(raw.get(k,'')) for k in ('company','role','location','description','source','language')}
    item['job_url']=canonical_url(raw.get('job_url',''))
    return item


def track_and_score(job):
    """Conservative triage heuristic, not applicant probability. No automatic hard-eligibility assertion."""
    title=job['role']; content=title+' '+job.get('description','')
    if CIVIL.search(title): track='Civil engineering'
    elif LOGISTICS.search(title): track='Logistics & supply chain'
    else: return None
    if SENIOR.search(title) and not JUNIOR.search(title): return None
    # Employment and remote labels are sometimes blank. Strict German focus on explicit non-German locations.
    loc=job.get('location','')
    if loc and not GERMANY.search(loc): return None
    score=45 + (15 if JUNIOR.search(title) else 0) + (8 if 'berlin' in loc.lower() else 0)
    score+= (5 if re.search('koordination|coordination|planning|planung|scheduling|construction|bau',content,re.I) else 0)
    score=min(75,score)
    flags=[]
    if re.search(r'\b(C1|C2)\b.{0,30}(?:deutsch|german)|(?:deutsch|german).{0,30}\b(C1|C2)\b|verhandlungssicheres deutsch',content,re.I): flags.append('German C1/C2 requirement: B1 gap; review manually')
    elif re.search(r'\bB2\b.{0,30}(?:deutsch|german)|(?:deutsch|german).{0,30}\bB2\b',content,re.I): flags.append('German B2 requirement: B1 gap; review manually')
    if re.search(r'führerschein|driving licen[cs]e|class b licence',content,re.I): flags.append('Driving licence requirement: unverified')
    if re.search(r'hoai|\bvob\b|rib itwo|revit|powerproject|autocad',content,re.I): flags.append('Specialist tools/standards mentioned: confirm practical proficiency')
    flags.append('Automated keyword match only; verify employer vacancy, eligibility, experience and opening before applying')
    return track,score,' | '.join(flags)


def collect_arbeitnow(session,pages=2):
    for page in range(1,min(max(int(pages),1),5)+1):
        url=f'https://www.arbeitnow.com/api/job-board-api?page={page}'
        resp=session.get(url,timeout=20,headers={'User-Agent':'ApplicationCenterJobTracker/1.0 (personal research)'})
        resp.raise_for_status()
        payload=resp.json()
        for x in payload.get('data',[]):
            yield normalize({'company':x.get('company_name'), 'role':x.get('title'), 'location':x.get('location'), 'job_url':x.get('url'), 'description':x.get('description'), 'source':'Arbeitnow public job API'})
        if not payload.get('data') or not payload.get('links',{}).get('next'): break


def collect_rss(session, feeds):
    import feedparser
    for f in feeds:
        url=f.get('url','')
        if not url.startswith('https://'): LOG.warning('Skipping invalid/insecure RSS URL: %s',url); continue
        resp=session.get(url,timeout=20)
        resp.raise_for_status()
        parsed=feedparser.parse(resp.content)
        for x in parsed.entries:
            yield normalize({'company':x.get('author') or f.get('company',''), 'role':x.get('title'), 'location':f.get('location','Germany'), 'job_url':x.get('link'), 'description':x.get('summary',''), 'source':f.get('name','RSS feed')})


def collect_greenhouse(session, boards):
    for b in boards:
        token=b.get('board_token','')
        if not re.fullmatch('[A-Za-z0-9_-]+',token): LOG.warning('Skipping invalid Greenhouse board token'); continue
        resp=session.get(f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs',params={'content':'true'},timeout=20)
        resp.raise_for_status()
        for x in resp.json().get('jobs',[]):
            loc=x.get('location') or {}
            yield normalize({'company':b.get('company',token),'role':x.get('title'),'location':loc.get('name',''), 'job_url':x.get('absolute_url'),'description':x.get('content',''), 'source':f'Greenhouse board: {token}'})




def collect_lever(session, boards):
    """Public Lever Postings API, configured company accounts only."""
    for b in boards:
        token=b.get('site','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid Lever site'); continue
        resp=session.get(f'https://api.lever.co/v0/postings/{token}',params={'mode':'json'},timeout=20)
        resp.raise_for_status()
        for x in resp.json():
            cats=x.get('categories') or {}
            loc=cats.get('location') or ''
            desc=x.get('descriptionPlain') or clean(x.get('description',''))
            yield normalize({'company':b.get('company',token),'role':x.get('text'),
                'location':loc,'job_url':x.get('hostedUrl') or x.get('applyUrl'),
                'description':desc,'source':f'Lever: {token}'})


def collect_smartrecruiters(session, companies):
    """Public SmartRecruiters postings API. Company IDs must be verified before activation."""
    for b in companies:
        token=b.get('company_id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid SmartRecruiters company ID'); continue
        for offset in (0, 100):
            resp=session.get(f'https://api.smartrecruiters.com/v1/companies/{token}/postings',
                             params={'limit':100,'offset':offset},timeout=20)
            resp.raise_for_status()
            payload=resp.json()
            for x in payload.get('content',[]):
                loc=x.get('location') or {}
                region=', '.join(str(loc.get(k,'')) for k in ('city','region','country') if loc.get(k))
                yield normalize({'company':b.get('company',token),'role':x.get('name'),
                    'location':region, 'job_url':x.get('ref') or x.get('postingUrl') or f'https://jobs.smartrecruiters.com/{token}/{x.get("id", "")}',
                    'description':'', 'source':f'SmartRecruiters: {token}'})
            if offset+len(payload.get('content',[])) >= payload.get('totalFound',0): break



def collect_ashby(session, boards):
    """Public Ashby board API; a verified organization slug is required."""
    for b in boards:
        token=b.get('board','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid Ashby board'); continue
        r=session.get(f'https://api.ashbyhq.com/posting-api/job-board/{token}',timeout=20)
        r.raise_for_status()
        for x in r.json().get('jobs',[]):
            if x.get('isListed') is False: continue
            yield normalize({'company':b.get('company',token),'role':x.get('title'),
                'location':x.get('location'),'job_url':x.get('jobUrl') or x.get('applyUrl'),
                'description':x.get('descriptionPlain') or x.get('descriptionHtml'),'source':f'Ashby: {token}'})


def collect_recruitee(session, boards):
    """Public Recruitee offers API; verified tenant slugs only."""
    for b in boards:
        token=b.get('site','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid Recruitee site'); continue
        r=session.get(f'https://{token}.recruitee.com/api/offers/',timeout=20)
        r.raise_for_status()
        for x in r.json().get('offers',[]):
            locations=x.get('locations') or []
            loc=x.get('city') or x.get('location') or ''
            if not loc and locations:
                loc=', '.join(z.get('city','') for z in locations if isinstance(z,dict))
            yield normalize({'company':b.get('company',token),'role':x.get('title'),
                'location':loc,'job_url':x.get('careers_url') or x.get('url'),
                'description':(x.get('description') or '')+' '+(x.get('requirements') or ''),
                'source':f'Recruitee: {token}'})


def collect_workable(session, boards):
    """Public Workable widget for configured employers."""
    for b in boards:
        token=b.get('account','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid Workable account'); continue
        r=session.get(f'https://apply.workable.com/api/v1/widget/accounts/{token}',
                      params={'details':'true'},timeout=20)
        r.raise_for_status()
        for x in r.json().get('jobs',[]):
            loc=x.get('location') or {}
            location=', '.join(str(loc.get(k,'')) for k in ('city','country') if loc.get(k)) if isinstance(loc,dict) else str(loc)
            yield normalize({'company':b.get('company',token),'role':x.get('title'),
                'location':location,'job_url':x.get('url') or x.get('shortlink'),
                'description':x.get('description') or '', 'source':f'Workable: {token}'})


def collect_personio(session, boards):
    """Public Personio XML listing; company tenant slugs must be verified."""
    for b in boards:
        token=b.get('tenant','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',token):
            LOG.warning('Skipping invalid Personio tenant'); continue
        domain=b.get('domain','de')
        if domain not in ('de','com'): domain='de'
        r=session.get(f'https://{token}.jobs.personio.{domain}/xml',timeout=20)
        r.raise_for_status()
        for x in ET.fromstring(r.content).findall('.//position'):
            val=lambda k: ''.join(x.findtext(k) or '').strip()
            desc=' '.join((d.text or '') for d in x.findall('.//jobDescription'))
            link=val('url') or f'https://{token}.jobs.personio.{domain}/job/{val("id")}'
            yield normalize({'company':b.get('company',token),'role':val('name'),
                'location':', '.join(k for k in (val('office'),val('city'),val('country')) if k),
                'job_url':link,'description':desc,'source':f'Personio: {token}'})



def active_search_terms(profiles, max_queries=8):
    """Round-robin active profiles so logistics isn't crowded out by civil title terms."""
    pools=[]
    for p in profiles or []:
        if not p.get('enabled'): continue
        terms=[]
        for term in p.get('terms',[]):
            term=clean(term)
            if 5<=len(term)<=70 and term.casefold() not in {x.casefold() for x in terms}:
                terms.append(term)
        if terms: pools.append(terms)
    results=[]
    while pools and len(results)<max(1,min(int(max_queries),25)):
        for terms in list(pools):
            if not terms:
                pools.remove(terms)
                continue
            term=terms.pop(0)
            if term.casefold() not in {x.casefold() for x in results}:
                results.append(term)
                if len(results)>=max_queries: break
        pools=[p for p in pools if p]
    return results

def collect_ba_jobs(session, profiles, settings):
    """Experimental BA Jobsuche interface documented by bundesAPI, not an official public API.

    Uses bounded job-title queries, request pacing and publicly accessible job-detail links.
    Stops on authentication, throttling or schema failures. Never bypasses protection.
    """
    terms=active_search_terms(profiles, max_queries=int(settings.get('max_queries',8)))
    if not terms: return
    base='https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs'
    headers={'X-API-Key':'jobboerse-jobsuche','Accept':'application/json',
             'User-Agent':'ApplicationCenterJobSearch/1.1 (individual job discovery)'}
    for term in terms:
        response=session.get(base,params={'was':term,'page':1,'size':min(int(settings.get('results_per_query',20)),25),
                     'angebotsart':1,'veroeffentlichtseit':min(int(settings.get('days',14)),30)},
                     headers=headers, timeout=22)
        response.raise_for_status()
        payload=response.json()
        offers=payload.get('stellenangebote')
        if not isinstance(offers,list):
            raise ValueError('Unexpected Bundesagentur response: stellenangebote is absent')
        for offer in offers:
            ref=offer.get('referenznummer') or offer.get('refnr') or ''
            if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}',str(ref)): continue
            loc=offer.get('arbeitsort') or offer.get('arbeitgeberAdresse') or {}
            if not isinstance(loc,dict): loc={}
            city=loc.get('ort') or loc.get('region') or 'Germany'
            country=loc.get('land') or 'Germany'
            location=f'{city}, {country}'
            yield normalize({'company':offer.get('arbeitgeber') or 'Unlisted employer',
                'role':offer.get('titel') or offer.get('stellenangebotsTitel') or offer.get('beruf'),
                'location':location,'job_url':f'https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}',
                'description':offer.get('stellenbeschreibung') or '',
                'source':'Bundesagentur Jobsuche (community-documented interface)'})


def collect_adzuna(session, profiles, settings):
    """Official documented Adzuna API: needs repository secrets ADZUNA_APP_ID/KEY."""
    app_id=os.getenv('ADZUNA_APP_ID','')
    app_key=os.getenv('ADZUNA_APP_KEY','')
    if not (app_id and app_key):
        LOG.info('Adzuna unconfigured: set both ADZUNA_APP_ID and ADZUNA_APP_KEY')
        return
    terms=active_search_terms(profiles, max_queries=int(settings.get('max_queries',8)))
    for term in terms:
        resp=session.get('https://api.adzuna.com/v1/api/jobs/de/search/1',
             params={'app_id':app_id,'app_key':app_key,'what':term,
                     'results_per_page':min(int(settings.get('results_per_query',20)),25),
                     'max_days_old':min(int(settings.get('days',14)),30),
                     'content-type':'application/json'},timeout=22)
        resp.raise_for_status()
        payload=resp.json()
        if not isinstance(payload.get('results'),list):
            raise ValueError('Unexpected Adzuna jobs response')
        for item in payload['results']:
            loc=item.get('location') or {}
            area=loc.get('display_name') or ', '.join(loc.get('area') or [])
            company=item.get('company') or {}
            yield normalize({'company':company.get('display_name') or 'Unlisted employer',
              'role':item.get('title'),'location':area or 'Germany',
              'job_url':item.get('redirect_url'), 'description':item.get('description') or '',
              'source':'Adzuna Germany official API'})


def dedup_key(item):
    url=canonical_url(item.get('job_url',''))
    if url: return 'u:'+url.casefold()
    return 't:'+'|'.join(re.sub(r'\W+',' ',clean(item.get(k,''))).casefold() for k in ('company','role','location'))


# User-controlled Role_Searches tab. These are TITLE terms, not arbitrary regular expressions.
# A term must match an individual job title; this avoids irrelevant role drift.
ROLE_HEADERS = ['profile_id', 'enabled', 'display_name', 'track', 'title_terms', 'notes']
VALID_TRACKS = {'Civil engineering', 'Logistics & supply chain', 'Project management', 'Operations', 'Other'}


def enabled_boolean(value):
    return str(value).strip().casefold() in ('true', 'yes', 'on', '1', 'ja')


def parse_role_rows(rows):
    """Parse exact six-column spreadsheet rows; disabled profiles remain visible but inactive."""
    if not rows or rows[0][:len(ROLE_HEADERS)] != ROLE_HEADERS:
        raise ValueError('Role_Searches header mismatch; expected ' + ', '.join(ROLE_HEADERS))
    profiles = []
    for number, row in enumerate(rows[1:], start=2):
        row = list(row) + [''] * (len(ROLE_HEADERS) - len(row))
        profile_id, enabled, name, track, terms, _notes = (str(x).strip() for x in row[:6])
        if not profile_id: continue
        if track not in VALID_TRACKS:
            LOG.warning('Ignoring Role_Searches row %d: invalid track %s', number, track)
            continue
        keywords = [x.strip().casefold() for x in terms.split(';') if x.strip()]
        if not keywords:
            LOG.warning('Ignoring Role_Searches row %d: no title terms', number)
            continue
        profiles.append({'id':profile_id, 'enabled':enabled_boolean(enabled),
                         'name':name or profile_id, 'track':track, 'terms':keywords})
    return profiles


def read_role_profiles(client, sheet_id):
    """Read the user's switches on every scheduled run. No Python edits necessary."""
    endpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Role_Searches!A1:F200'
    response = client.get(endpoint, timeout=30)
    response.raise_for_status()
    return parse_role_rows(response.json().get('values', []))


# A generic "Project Engineer" title is not sufficient evidence of a civil role.
GENERAL_ENGINEER = re.compile(r'^(?:junior\s+)?(?:projekt(?:ingenieur|engineer)|project engineer|engineering project manager)', re.I)
CONSTRUCTION_CONTEXT = re.compile(r'bau\b|construction|civil|infrastructure|hochbau|tiefbau|wohnungsbau|baustell|building|structural|water engineering|wasserbau|brücken|bridge',re.I)
NON_CIVIL_DOMAINS = re.compile(r'medizintechnik|medical device|clinical|pharma|elektrotechnik|electrical|software|embedded|automotive|maschinenbau|mechanical engineering|automation engineer',re.I)


def profile_match(job, profiles):
    title = clean(job.get('role', '')).casefold()
    location = job.get('location', '')
    if location and not GERMANY.search(location): return None
    # Hard reject explicit executive roles regardless of profile selection.
    if re.search(r'\b(director|vice president|\bvp\b|chief executive|head of)\b', title, re.I): return None
    for p in profiles:
        if p['enabled'] and any(term in title for term in p['terms']):
            if p['track']=='Civil engineering':
                broad = GENERAL_ENGINEER.search(title)
                if broad and (NON_CIVIL_DOMAINS.search(title) or not CONSTRUCTION_CONTEXT.search(title+' '+job.get('description',''))):
                    continue

            score = 48 + (12 if JUNIOR.search(title) else 0) + (8 if 'berlin' in location.lower() else 0)
            score += (4 if re.search(r'planung|koordination|project|projekt|teamlead|teamleiter|schichtleiter', title, re.I) else 0)
            _base = track_and_score(job)
            notes = _base[2] if _base else 'Title-based match only; verify employer vacancy, language, experience and qualifications'
            return p['track'], min(76, score), f'Search profile: {p["name"]} | {notes}'
    return None


def filter_jobs(raw,seen_urls=None,seen_triples=None,profiles=None):
    seen_urls=set(seen_urls or [])
    seen_triples=set(seen_triples or [])
    found=[]
    for src in raw:
        job=normalize(src)
        if not job['job_url'] or not job['company'] or not job['role']: continue
        tri=tuple(clean(job[k]).casefold() for k in ('company','role','location'))
        if job['job_url'] in seen_urls or tri in seen_triples: continue
        result=profile_match(job,profiles) if profiles is not None else track_and_score(job)
        if not result: continue
        track,fit,notes=result
        job.update(track=track,fit=fit,notes=notes,status='discovered')
        seen_urls.add(job['job_url']);seen_triples.add(tri)
        found.append(job)
    return sorted(found,key=lambda x:x['fit'],reverse=True)


def get_client():
    import google.auth
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    value=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','')
    if not value: raise RuntimeError('Missing GOOGLE_SERVICE_ACCOUNT_JSON secret')
    credentials=service_account.Credentials.from_service_account_info(json.loads(value),scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return AuthorizedSession(credentials)


def read_existing(client,sheet_id):
    url=f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Jobs!A1:T10000'
    r=client.get(url,timeout=30);r.raise_for_status()
    values=r.json().get('values',[])
    if not values or values[0][:len(HEADERS)]!=HEADERS: raise RuntimeError('Jobs sheet headers mismatch; refusing write')
    urls=set();triples=set()
    for row in values[1:]:
        row=row+['']*(len(HEADERS)-len(row))
        urls.add(canonical_url(row[5]))
        triples.add(tuple(clean(row[i]).casefold() for i in (1,2,4)))
    return {u for u in urls if u},triples,len(values)-1


def append_jobs(client,sheet_id,jobs):
    if not jobs:return 0
    from uuid import uuid4
    today=datetime.now(ZoneInfo('Europe/Berlin')).date().isoformat()
    rows=[]
    for j in jobs:
        d={**j,'id':str(uuid4()),'discovered_at':today,'updated_at':today}
        rows.append([("'"+d[k] if isinstance(d.get(k),str) and d[k].lstrip().startswith(('=','+','-','@')) else d.get(k,'')) for k in HEADERS])
    # Existing data never overwritten. Only append new rows.
    endpoint=f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Jobs!A:T:append'
    r=client.post(endpoint,params={'valueInputOption':'USER_ENTERED','insertDataOption':'INSERT_ROWS'},json={'values':rows},timeout=35)
    r.raise_for_status()
    return len(rows)



COLLECTOR_ORDER = ['Arbeitnow','Bundesagentur','Adzuna','RSS','Greenhouse','Lever','SmartRecruiters','Ashby','Recruitee','Workable','Personio']


def update_source_health(client, sheet_id, results, cfg):
    """Best-effort operational visibility; never overwrite application records."""
    by_name={n:(count,status) for n,count,status in results}
    enabled={'Arbeitnow':bool(cfg.get('arbeitnow',{}).get('enabled')),
             'Bundesagentur':bool(cfg.get('bundesagentur',{}).get('enabled')),
             'Adzuna':bool(cfg.get('adzuna',{}).get('enabled') and os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY')),
             **{n:bool(cfg.get(n.lower(),[])) for n in COLLECTOR_ORDER[3:]}}
    timestamp=datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M')
    rows=[['collector','enabled','last_run_berlin','records_fetched','status','detail']]
    for name in COLLECTOR_ORDER:
        count,status=by_name.get(name,(0,'inactive'))
        rows.append([name,'TRUE' if enabled.get(name) else 'FALSE',
                     timestamp if enabled.get(name) else '',
                     count if enabled.get(name) else '',
                     'OK' if status=='ok' else ('Inactive' if status=='inactive' else 'Error'),
                     '' if status in ('ok','inactive') else str(status)[:160]])
    endpoint=f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Source_Health!A1:F12'
    try:
        r=client.put(endpoint,params={'valueInputOption':'RAW'},json={'values':rows},timeout=30)
        r.raise_for_status()
    except (requests.RequestException,AttributeError) as exc:
        LOG.warning('Source_Health update unavailable: %s',exc)



def append_run_history(client, sheet_id, source_count, matches, saved, profiles, source_results):
    """Append a compact audit record; never change or reclassify existing applications."""
    now=datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M')
    enabled='; '.join(p['name'] for p in profiles if p['enabled'])
    errors='; '.join(name+': '+status[:80] for name,_,status in source_results if status!='ok')
    endpoint=f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Run_History!A:F:append'
    try:
        response=client.post(endpoint,params={'valueInputOption':'RAW','insertDataOption':'INSERT_ROWS'},
            json={'values':[[now,source_count,matches,saved,enabled,errors]]},timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOG.warning('Run_History append unavailable: %s',exc)


def run(config_path='config/sources.json',dry_run=False,limit=30,sheet_id=SHEET_ID):
    cfg=json.loads(Path(config_path).read_text(encoding='utf-8'))
    session=requests.Session()
    # Read live search switches BEFORE issuing source queries.
    client=None
    if dry_run:
        profile_data=json.loads(Path('config/role_profiles.json').read_text(encoding='utf-8'))
        profiles=parse_role_rows([ROLE_HEADERS]+[[p.get(k,'') for k in ROLE_HEADERS] for p in profile_data])
    else:
        client=get_client()
        profiles=read_role_profiles(client,sheet_id)
    candidates=[]
    collectors=[]
    if cfg.get('arbeitnow',{}).get('enabled',False):
        collectors.append(('Arbeitnow',lambda:collect_arbeitnow(session,cfg.get('arbeitnow',{}).get('pages',2))))
    if cfg.get('bundesagentur',{}).get('enabled'):
        collectors.append(('Bundesagentur',lambda:collect_ba_jobs(session,profiles,cfg['bundesagentur'])))
    if cfg.get('adzuna',{}).get('enabled'):
        collectors.append(('Adzuna',lambda:collect_adzuna(session,profiles,cfg['adzuna'])))
    if cfg.get('rss'):
        collectors.append(('RSS',lambda:collect_rss(session,cfg.get('rss',[]))))
    if cfg.get('greenhouse'):
        collectors.append(('Greenhouse',lambda:collect_greenhouse(session,cfg.get('greenhouse',[]))))
    if cfg.get('lever'):
        collectors.append(('Lever',lambda:collect_lever(session,cfg.get('lever',[]))))
    if cfg.get('smartrecruiters'):
        collectors.append(('SmartRecruiters',lambda:collect_smartrecruiters(session,cfg.get('smartrecruiters',[]))))
    for key,func,label in [('ashby',collect_ashby,'Ashby'),
                           ('recruitee',collect_recruitee,'Recruitee'),
                           ('workable',collect_workable,'Workable'),
                           ('personio',collect_personio,'Personio')]:
        if cfg.get(key):
            collectors.append((label,lambda fn=func,k=key:fn(session,cfg.get(k,[]))))
    source_results=[]
    for label,collector in collectors:
        try:
            batch=list(collector());candidates.extend(batch);LOG.info('%s: fetched %s',label,len(batch));source_results.append((label,len(batch),'ok'))
        except (requests.RequestException,ValueError,KeyError) as e:
            LOG.error('%s source failed: %s',label,e);source_results.append((label,0,'error: '+str(e)[:160]))
    if not candidates: LOG.warning('No source results; leaving Sheets unchanged')
    if dry_run:
        selected=filter_jobs(candidates,profiles=profiles)[:limit]
        print(json.dumps({'dry_run':True,'found':len(candidates),'eligible_for_manual_review':len(selected),'jobs':selected},ensure_ascii=False,indent=2))
        return selected
    enabled_names = [p['name'] for p in profiles if p['enabled']]
    LOG.info('Enabled search profiles: %s', enabled_names)
    urls,triples,_=read_existing(client,sheet_id)
    selected=filter_jobs(candidates,urls,triples,profiles=profiles)[:limit]
    count=append_jobs(client,sheet_id,selected)
    update_source_health(client,sheet_id,source_results,cfg)
    append_run_history(client,sheet_id,len(candidates),len(selected),count,profiles,source_results)
    print(json.dumps({'source_records':len(candidates),'new_saved':count,'sources':[{'name':n,'records':q,'status':st} for n,q,st in source_results], 'job_titles':[x['role'] for x in selected]},ensure_ascii=False))
    return selected


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--config',default='config/sources.json')
    p.add_argument('--limit',type=int,default=30)
    p.add_argument('--sheet-id',default=SHEET_ID)
    p.add_argument('--scheduled',action='store_true',help='Only run at 8 AM Berlin local time')
    args=p.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    if args.scheduled and datetime.now(ZoneInfo('Europe/Berlin')).hour!=8:
        print('Outside 08:00 Europe/Berlin; skipping DST crossover cron trigger');return
    run(args.config,args.dry_run,max(1,min(args.limit,100)),args.sheet_id)

if __name__=='__main__':main()
