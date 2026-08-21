from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
class Candidate(BaseModel):
    source_name:str; source_url:str; title:str=''; organisation:str=''; post:str=''
    published_date:Optional[date]=None; last_date:Optional[date]=None
    notification_url:str=''; application_url:str=''; discovery_text:str=''
class Recruitment(BaseModel):
    organisation:str=''; ministry_department:str=''; recruiting_body:str=''; post_title:str=''
    vacancies_total:Optional[int]=None; advertisement_number:str=''; notification_number:str=''
    publication_date:Optional[date]=None; updated_date:Optional[date]=None
    application_start_date:Optional[date]=None; application_end_date:Optional[date]=None
    qualification:str=''; experience:str=''; age_limit:str=''; age_relaxation:str=''
    pay_scale:str=''; pay_level:str=''; salary:str=''; category_requirements:str=''; application_fee:str=''
    application_url:str=''; notification_url:str=''; official_source_url:str=''; official_domain:str=''
    important_instructions:list[str]=Field(default_factory=list); selection_process:str=''; job_location:str=''
    source_name:str=''; source_verified:bool=False; extraction_confidence:float=0.0
    fingerprint:str=''; document_hash:str=''; source_document:str=''; notes:str=''
    def as_dict(self): return self.model_dump(mode='json')
