import sys,re,csv,pandas as pd,numpy as np
dd=sys.argv[1]
def ts(f):
    rows=[l for l in open(f,encoding='latin-1').read().splitlines() if re.match(r'^\d{4},',l)]
    return pd.Series({int(r[0]):int(r[5].replace(',','')) for r in csv.reader(rows)})
cm=ts(f'{dd}/cmhc/ts_csd_comp.csv'); cs=ts(f'{dd}/cmhc/ts_csd_starts.csv')
p=pd.read_parquet(f'{dd}/permits_all.parquet')
p['suf']=p.PERMIT_NUM.str.split().str[-1]; p['stem']=p.PERMIT_NUM.str.rsplit(' ',n=1).str[0]
p['pr']=p.src.map({'act':3,'c17':2,'c00':1}); p['k']=p.PERMIT_NUM+'|'+p.REVISION_NUM+'|'+p.PERMIT_TYPE.fillna('')
d=p.sort_values('pr').drop_duplicates('k',keep='last')
b=d[(d.suf.str.match(r'^(BLD|B\d\d|000)$'))&(d.DWELLING_UNITS_CREATED>0)&(d.DWELLING_UNITS_CREATED<5000)]
bp=b.sort_values('REVISION_NUM').groupby('PERMIT_NUM').agg(units=('DWELLING_UNITS_CREATED','max'),comp=('COMPLETED_DATE','max'),iss=('ISSUED_DATE','min'),status=('STATUS','last'),stem=('stem','first'),work=('WORK','first'))
bp['cy']=bp.comp.dt.year; bp['iy']=bp.iss.dt.year
nb=bp[bp.work.str.contains('New Building',na=False)]
t=pd.DataFrame({'CMHC_starts':cs,'CMHC_completions':cm,
 'permit_units_issued_NB':nb.groupby('iy').units.sum(),
 'permit_units_cleared_NB_Closed':nb[nb.status=='Closed'].groupby('cy').units.sum()})
t['cleared/CMHC_comp']=(t.permit_units_cleared_NB_Closed/t.CMHC_completions).round(2)
t['issued/CMHC_starts']=(t.permit_units_issued_NB/t.CMHC_starts).round(2)
print(t.loc[1999:2026].to_string())
print('\n3-yr rolling corr (2002-2025) cleared vs CMHC comp:',t.loc[2002:2025,['permit_units_cleared_NB_Closed','CMHC_completions']].corr().iloc[0,1].round(2))
print('issued vs starts corr:',t.loc[2002:2025,['permit_units_issued_NB','CMHC_starts']].corr().iloc[0,1].round(2))
ss=bp[bp.work.str.contains('Second Suite|Laneway|Garden',na=False)]
print('\nSecond suite / laneway / garden permit units issued by year:',ss.groupby('iy').units.sum().loc[2015:2026].astype(int).to_dict())
mp=nb[(nb.units>=2)&(nb.units<=6)]
print('New Building 2-6 unit permits issued by year (count):',mp.groupby('iy').size().loc[2015:2026].to_dict())
t.to_csv(f'{dd}/reconcile.csv')
