from src.discovery.generic import GenericHTMLSource
def build_sources(config): return [GenericHTMLSource(s) for s in config.get('sources',[])]
