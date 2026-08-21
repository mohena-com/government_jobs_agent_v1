from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.models import Candidate
from src.utils.http import get
class GenericHTMLSource:
    def __init__(self,config): self.config=config
    def discover(self,since,until):
        r=get(self.config['url']); r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml'); out=[]; seen=set()
        keys=['recruit','vacanc','advert','job','post','notice','career','employment']
        for a in soup.find_all('a',href=True):
            text=' '.join(a.get_text(' ',strip=True).split()); low=text.lower()
            if not text or not any(k in low for k in keys): continue
            href=urljoin(r.url,a['href']); key=(text,href)
            if key in seen: continue
            seen.add(key); out.append(Candidate(source_name=self.config['name'],source_url=r.url,title=text,notification_url=href if '.pdf' in href.lower() or 'notice' in low or 'advert' in low else '',application_url=href if 'apply' in low else '',discovery_text=text))
        return out[:200]
