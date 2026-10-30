import sys, pandas as pd, numpy as np
p=pd.read_parquet(sys.argv[1])
p['ay']=p.APPLICATION_DATE.dt.year; p['cy']=p.COMPLETED_DATE.dt.year; p['iy']=p.ISSUED_DATE.dt.year
print('APPLICATION_DATE range by src:'); print(p.groupby('src').APPLICATION_DATE.agg(['min','max']).to_string())
print('COMPLETED_DATE range by src:'); print(p.groupby('src').COMPLETED_DATE.agg(['min','max']).to_string())
print('\nRows by application year x src'); print(pd.crosstab(p.ay,p.src).loc[1997:2026].to_string())
print('\nRows by completed year x src'); print(pd.crosstab(p.cy,p.src).loc[1999:2026].to_string())
# dedupe on key; overlap between files
p['k']=p.PERMIT_NUM+'|'+p.REVISION_NUM+'|'+p.PERMIT_TYPE.fillna('')
ov=p.groupby('k').src.agg(lambda s:'+'.join(sorted(set(s))))
print('\nkey overlap patterns:',ov.value_counts().to_dict())
# Residential new construction units: PERMIT_TYPE New Houses / New Building / Residential Building Permit? use units>0 & revision 00
p['stem']=p.PERMIT_NUM.str.rsplit(' ',n=1).str[0]
u=p[(p.DWELLING_UNITS_CREATED>0)]
print('\nPermits with UNITS_CREATED>0 by PERMIT_TYPE:'); print(u.PERMIT_TYPE.value_counts().head(15).to_string())
print('by suffix:',u.PERMIT_NUM.str.split().str[-1].value_counts().head(10).to_dict())
print('by revision:',u.REVISION_NUM.value_counts().head(5).to_dict())
# Units created by application year, rev 00 only, BLD suffix, dedup key keep last src priority act>c17>c00
pr={'act':3,'c17':2,'c00':1}; p['pr']=p.src.map(pr)
d=p.sort_values('pr').drop_duplicates('k',keep='last')
b=d[(d.PERMIT_NUM.str.endswith('BLD'))&(d.DWELLING_UNITS_CREATED>0)]
# per stem: max units across revisions
st=b.groupby('stem').agg(units=('DWELLING_UNITS_CREATED','max'),units_sum=('DWELLING_UNITS_CREATED','sum'),nrev=('REVISION_NUM','nunique'),
  app=('APPLICATION_DATE','min'),iss=('ISSUED_DATE','min'),comp=('COMPLETED_DATE','max'),status=('STATUS','last'),geo=('GEO_ID','first'),src=('src','last'),lost=('DWELLING_UNITS_LOST','max'))
st['ay']=st.app.dt.year
print('\nBLD stems with units>0:',len(st),' max-vs-sum diff units:',(st.units_sum-st.units).sum())
t=st.groupby('ay').agg(stems=('units','size'),units=('units','sum'),issued=('iss',lambda s:s.notna().mean()),closed=('status',lambda s:(s=='Closed').mean()),cancel=('status',lambda s:s.str.contains('Cancel',na=False).mean()),dormant=('status',lambda s:(s=='Closed - Dormant').mean()))
print(t.loc[1998:2026].round(3).to_string())
st['lag_app_iss']=(st.iss-st.app).dt.days/365.25; st['lag_iss_comp']=(st.comp-st.iss).dt.days/365.25
big=st[st.units>=50]
print('\n50+ unit BLD stems:',len(big),'median yrs app->issue',big.lag_app_iss.median().round(2),'issue->cleared',big.lag_iss_comp.median().round(2))
print('share 50+ unit stems issued 2010-2018 that are cleared by now:', big[(big.iss.dt.year>=2010)&(big.iss.dt.year<=2018)].comp.notna().mean().round(3))
small=st[st.units<=4]
print('<=4 unit stems: median yrs issue->cleared',small.lag_iss_comp.median().round(2))
# lost units fill
print('\nDWELLING_UNITS_LOST non-null share by app year (dedup):'); print(d.groupby('ay').DWELLING_UNITS_LOST.apply(lambda s:s.notna().mean()).loc[1999:2026].round(3).to_dict())
dm=d[d.PERMIT_TYPE.str.contains('Demolition',na=False)]
print('Demolition Folder permits by ay (n, share with lost>0):'); print(dm.groupby('ay').agg(n=('k','size'),pos=('DWELLING_UNITS_LOST',lambda s:(s>0).mean()),lost=('DWELLING_UNITS_LOST','sum')).loc[2000:2026].round(3).to_string())
st.to_parquet(sys.argv[2])
