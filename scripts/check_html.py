from html.parser import HTMLParser
from pathlib import Path
class Document(HTMLParser):
    def __init__(self): super().__init__(); self.stack=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'Duplicate id: '+attrs['id']
            self.ids.add(attrs['id'])
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(tag)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack and self.stack[-1]==tag:self.handle_endtag(tag)
    def handle_endtag(self,tag):assert self.stack.pop()==tag, 'Unbalanced '+tag
p=Document();p.feed((Path(__file__).resolve().parents[1]/'web/index.html').read_text());assert not p.stack
print('Document structure verified')
