import sys, pandas as pd, numpy as np
raw=sys.argv[1]; out=sys.argv[2]
fs={'c00':'building-permits-cleared-permits__Cleared_Permits_2000_to_2016.csv','c17':'building-permits-cleared-permits__Cleared_Building_Permits_since_2017.csv','act':'building-permits-active-permits__building-permits-active-permits.csv'}
ds=[]
for k,f in fs.items():
    d=pd.read_csv(f'{raw}/{f}',dtype=str,low_memory=False); d.columns=[c.upper() for c in d.columns]; d['src']=k; ds.append(d)
p=pd.concat(ds,ignore_index=True)
for c in ['APPLICATION_DATE','ISSUED_DATE','COMPLETED_DATE']:
    p[c]=pd.to_datetime(p[c].str[:10],errors='coerce',format='%Y-%m-%d')
for c in ['DWELLING_UNITS_CREATED','DWELLING_UNITS_LOST','RESIDENTIAL','DEMOLITION']:
    p[c]=pd.to_numeric(p[c],errors='coerce')
p.drop(columns=['_ID'],errors='ignore').to_parquet(out)
print(p.shape)
