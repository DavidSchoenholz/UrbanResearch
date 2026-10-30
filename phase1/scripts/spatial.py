import sys,json,pandas as pd,numpy as np,geopandas as gpd
from shapely.geometry import shape, Point
raw=sys.argv[1]; dd=sys.argv[2]
ap=pd.read_csv(f'{raw}/address_points_2952.csv',dtype=str,usecols=['ADDRESS_POINT_ID','ADDRESS_ID','ADDRESS_STATUS','MAINT_STAGE','geometry'])
print('address points',len(ap),ap.ADDRESS_STATUS.value_counts().to_dict(),ap.MAINT_STAGE.value_counts().to_dict())
print('geom sample',ap.geometry.iloc[0][:120])
p=pd.read_parquet(f'{dd}/permits_all.parquet',columns=['PERMIT_NUM','GEO_ID','APPLICATION_DATE','DWELLING_UNITS_CREATED','WORK','src'])
p['ay']=p.APPLICATION_DATE.dt.year
for k in ['ADDRESS_POINT_ID','ADDRESS_ID']:
    m=p.GEO_ID.isin(set(ap[k]))
    print(f'GEO_ID matches {k}:',m.mean().round(3))
ap['xy']=ap.geometry.map(lambda g: json.loads(g)['coordinates'] if isinstance(g,str) and g.startswith('{') else None)
ap=ap[ap.xy.notna()].copy()
ap['x']=ap.xy.map(lambda c:c[0] if not isinstance(c[0],list) else c[0][0]); ap['y']=ap.xy.map(lambda c:c[1] if not isinstance(c[0],list) else c[0][1])
p['m']=p.GEO_ID.isin(set(ap.ADDRESS_POINT_ID))
print('GEO_ID->current address point match by application year:'); print(p.groupby('ay').m.mean().loc[2000:2026].round(3).to_dict())
nr=p[(p.DWELLING_UNITS_CREATED>0)&p.WORK.fillna('').str.contains('New Building')].copy()
print('new-res permits geo match:',nr.m.mean().round(3))
pts=nr.merge(ap[['ADDRESS_POINT_ID','x','y']],left_on='GEO_ID',right_on='ADDRESS_POINT_ID')
g=gpd.GeoDataFrame(pts,geometry=gpd.points_from_xy(pts.x,pts.y),crs=2952)
z=gpd.read_file(f'{raw}/zoning-by-law__Zoning_Area_-_2952.gpkg')
print('zoning crs',z.crs,len(z)); print('ZN_STATUS counts',z.ZN_STATUS.value_counts().to_dict())
print('ZN_HOLDING',z.ZN_HOLDING.value_counts().to_dict(),'ZN_EXCPTN',z.ZN_EXCPTN.value_counts().to_dict())
print('GEN_ZONE counts',z.GEN_ZONE.value_counts().to_dict())
for c in ['FSI_TOTAL','DENSITY','UNITS','PRCNT_RES','COVERAGE']:
    v=pd.to_numeric(z[c],errors='coerce'); print(c,'share>0:',(v>0).mean().round(3))
print('ZN_STRING sample',z.ZN_STRING.dropna().sample(8,random_state=3).tolist())
if z.crs and z.crs.to_epsg()!=2952: z=z.to_crs(2952)
j=gpd.sjoin(g,z[['ZN_STATUS','ZN_HOLDING','ZN_EXCPTN','GEN_ZONE','ZN_ZONE','FSI_TOTAL','DENSITY','ZN_STRING','geometry']],how='left',predicate='within')
j=j[~j.index.duplicated()]
j['inzone']=j.ZN_STATUS.notna()
j['not569']=j.ZN_STATUS.astype(str)=='5'
j['exc']=j.ZN_EXCPTN=='Y'; j['hold']=j.ZN_HOLDING=='Y'
j['fsi_or_d']=(pd.to_numeric(j.FSI_TOTAL,errors='coerce')>0)|(pd.to_numeric(j.DENSITY,errors='coerce')>0)
j['size']=pd.cut(j.DWELLING_UNITS_CREATED,[0,1,4,49,1e9],labels=['1','2-4','5-49','50+'])
print('\nNew-res permits (geocoded) zoning attributes by size:')
print(j.groupby('size')[['inzone','not569','exc','hold','fsi_or_d']].mean().round(3).to_string())
print('by app year (all sizes):'); print(j.groupby('ay')[['not569','exc','hold']].mean().loc[2005:2026].round(3).to_string())
