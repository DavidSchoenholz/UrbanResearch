import json,sys,glob,os
for f in sorted(glob.glob(os.path.join(sys.argv[1],'pkg_*.json'))):
    p=json.load(open(f))['result']
    print('=====',p['name'],'|',p.get('title'))
    for k in ['owner_division','owner_section','refresh_rate','last_refreshed','metadata_modified','license_title','license_url','formats','information_url','dataset_category','is_retired','limitations']:
        if p.get(k): print(f'  {k}: {str(p.get(k))[:400]}')
    print('  excerpt:',(p.get('excerpt') or '')[:300].replace('\n',' '))
    for r in p['resources']:
        print(f"   - R {r['name']} | {r.get('format')} | datastore={r.get('datastore_active')} | modified={r.get('last_modified')} | id={r['id']}")
