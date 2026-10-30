import sys,re,pandas as pd,numpy as np
raw=sys.argv[1]; dd=sys.argv[2]; pd.set_option('display.width',250)
da=pd.read_csv(f'{raw}/development-applications__Development_Applications.csv',dtype=str)
da['d']=pd.to_datetime(da.DATE_SUBMITTED.str[:10],errors='coerce'); da['y']=da.d.dt.year; da['STATUS']=da.STATUS.str.strip()
u=da.drop_duplicates('APPLICATION#')
print('unique apps by year x type'); print(pd.crosstab(u.y,u.APPLICATION_TYPE).to_string())
oz=u[u.APPLICATION_TYPE=='OZ']
print('\nOZ status by submission year (share):'); print(pd.crosstab(oz.y,oz.STATUS,normalize='index').round(2)[['Closed','Under Review','OMB Appeal','OMB Approved','Appeal Received','Council Approved']].to_string())
print('rows per app:',da.groupby('APPLICATION#').size().describe().round(1).to_dict())
def norm(num,name,typ,dirn):
    s=' '.join(str(x).strip().upper() for x in [num,name,typ,dirn] if isinstance(x,str) and x.strip())
    return re.sub(r'\s+',' ',s)
p=pd.read_parquet(f'{dd}/permits_all.parquet')
p['addr']=[norm(a,b,c,d) for a,b,c,d in zip(p.STREET_NUM,p.STREET_NAME,p.STREET_TYPE,p.STREET_DIRECTION)]
p['stem']=p.PERMIT_NUM.str.rsplit(' ',n=1).str[0]
newres=p[(p.DWELLING_UNITS_CREATED>0)&(p.WORK.fillna('').str.contains('New Building'))]
addr_set=set(p.addr)
pl=pd.read_csv(f'{raw}/development-pipeline__Development_Pipeline.csv',dtype=str)
pl['addr']=pl.Address.fillna('').str.upper().str.replace(r'\s+',' ',regex=True).str.strip()
pl['units']=pd.to_numeric(pl['Proposed Residential Units'],errors='coerce')
pl['any_permit_addr']=pl.addr.isin(addr_set)
pl['newres_addr']=pl.addr.isin(set(newres.addr))
print('\nPipeline: share whose Address string exactly matches some permit address / a new-residential permit address')
print(pl.groupby('Pipeline Status')[['any_permit_addr','newres_addr']].mean().round(3).to_string())
pr=pl[pl.units>0]
print('residential-only (units>0):'); print(pr.groupby('Pipeline Status')[['any_permit_addr','newres_addr']].mean().round(3).to_string())
# devapps address too
da['addr']=[norm(a,b,c,d) for a,b,c,d in zip(da.STREET_NUM,da.STREET_NAME,da.STREET_TYPE,da.STREET_DIRECTION)]
ozr=da[da.APPLICATION_TYPE=='OZ']
g=ozr.groupby('APPLICATION#').agg(addrs=('addr',lambda s:set(s)),y=('y','first'),st=('STATUS','first'))
g['m']=[bool(a & addr_set) for a in g.addrs]
g['mres']=[bool(a & set(newres.addr)) for a in g.addrs]
print('\nOZ apps with any address row matching a permit address / new-res permit, by year:'); print(g.groupby('y')[['m','mres']].mean().round(3).to_string())
# new-res permit projects matched to OZ address (as-of-right share proxy) by permit app year
nr=newres.groupby('stem').agg(addr=('addr','first'),units=('DWELLING_UNITS_CREATED','sum'),ay=('APPLICATION_DATE',lambda s:s.min().year))
ozaddr=set().union(*g.addrs)
coa=pd.read_csv(f'{raw}/committee-of-adjustment-applications__Closed_Applications_since_2017.csv',dtype=str)
coa['addr']=[norm(a,b,c,d) for a,b,c,d in zip(coa.STREET_NUM,coa.STREET_NAME,coa.STREET_TYPE,coa.STREET_DIRECTION)]
mvaddr=set(coa[coa.APPLICATION_TYPE=='MV'].addr)
nr['oz']=nr.addr.isin(ozaddr); nr['mv']=nr.addr.isin(mvaddr)&~nr.oz
nr['cls']=np.select([nr.oz,nr.mv],['OZ-linked','MV-linked'],'no link')
nr['size']=pd.cut(nr.units,[0,1,4,49,1e9],labels=['1','2-4','5-49','50+'])
t=nr[(nr.ay>=2018)&(nr.ay<=2025)]
print('\nNew-residential permit projects 2018-2025 by size x address-link class (share of projects):')
print(pd.crosstab(t['size'],t.cls,normalize='index').round(3).to_string())
print('units share:'); print(t.groupby(['size','cls']).units.sum().unstack().div(t.groupby('size').units.sum(),axis=0).round(3).to_string())
