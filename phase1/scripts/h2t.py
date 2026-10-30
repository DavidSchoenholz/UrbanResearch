import sys,re,html
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in('script','style','noscript','svg'): s.skip+=1
        if t in('p','br','li','h1','h2','h3','h4','tr','div','td'): s.out.append('\n')
        if t=='a':
            h=dict(a).get('href');
            if h and not s.skip: s.out.append(f' [{h}] ')
    def handle_endtag(s,t):
        if t in('script','style','noscript','svg'): s.skip=max(0,s.skip-1)
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
p=P(); p.feed(open(sys.argv[1],encoding='utf-8',errors='ignore').read())
t=re.sub(r'\n\s*\n+','\n',''.join(p.out)); print(t)
