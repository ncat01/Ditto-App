"""SerpApi Google Lens on original images or five sampled video frames.
Search returns unverified links; it neither fetches arbitrary URLs nor asserts infringement.
"""
import base64, io
from urllib.parse import urlsplit
import cv2, httpx
from PIL import Image, ImageOps
from app.config import get_settings

class SearchUnavailable(RuntimeError): pass


def result_items(row, result_key):
    """A successful empty Google response is not a provider outage."""
    if not isinstance(row, dict):
        raise ValueError('Invalid search response')
    metadata = row.get('search_metadata', {})
    if not isinstance(metadata, dict):
        raise ValueError('Invalid search metadata')
    status = metadata.get('status')
    if status is not None and status != 'Success':
        raise SearchUnavailable('Reverse search unavailable. Try again later.')
    error = row.get('error')
    if error is not None and not isinstance(error, str):
        raise ValueError('Invalid search error')
    empty_messages = {
        "Google hasn't returned any results for this query.",
        "Google Lens hasn't returned any results for this query.",
        "Google Reverse Image hasn't returned any results for this query.",
    }
    if error and not (status == 'Success' and error.strip() in empty_messages):
        raise SearchUnavailable('Reverse search unavailable. Try again later.')
    items = row.get(result_key)
    if items is None:
        if status == 'Success':
            return []
        raise ValueError('Missing search results')
    if not isinstance(items, list):
        raise ValueError('Invalid search results')
    return items


def query_images(path,kind):
    encoded=[]
    def append(image):
        image.thumbnail((1280,1280))
        buffer=io.BytesIO()
        image.convert('RGB').save(buffer,format='JPEG',quality=85)
        encoded.append(base64.b64encode(buffer.getvalue()).decode())
    if kind=='video':
        capture=cv2.VideoCapture(str(path))
        try:
            if not capture.isOpened():raise ValueError('Video cannot be decoded')
            count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            for i in range(5):
                capture.set(cv2.CAP_PROP_POS_FRAMES,int(max(count-1,0)*i/4))
                ok,frame=capture.read()
                if not ok:raise ValueError('Video frame cannot be decoded')
                append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
        finally:capture.release()
    else:
        with Image.open(path) as source:
            if source.width*source.height>40000000:raise ValueError('Image is too large')
            append(ImageOps.exif_transpose(source).convert('RGB'))
    return encoded

def safe_url(value):
    if not isinstance(value,str) or len(value)>2048:return None
    try:
        uri=urlsplit(value)
        if uri.scheme not in ('http','https') or not uri.hostname or uri.username or uri.password:return None
        return value
    except ValueError:return None

def search(images):
    key=get_settings().serpapi_api_key.get_secret_value()
    if not key:raise SearchUnavailable('Web search is not configured by the service operator.')
    results={}
    try:
        with httpx.Client(timeout=45,follow_redirects=False) as client:
            for frame,encoded in enumerate(images):
                # SerpApi accepts uploads up to 500 KB. Resize before any upload.
                with Image.open(io.BytesIO(base64.b64decode(encoded,validate=True))) as source:
                    image=source.convert('RGB');image.thumbnail((1024,1024))
                    for quality in (80,65,45,30):
                        buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=quality)
                        data=buffer.getvalue()
                        if len(data)<=490000:break
                    if len(data)>490000:raise ValueError('Search image too large')
                uploaded=client.post('https://serpapi.com/image',data={'api_key':key},files={'image':('frame.jpg',data,'image/jpeg')})
                if uploaded.status_code!=200:raise SearchUnavailable('Search image upload unavailable. Try again later.')
                image_id=uploaded.json().get('image_id')
                if not isinstance(image_id,str) or not image_id:raise ValueError()
                # Google Lens exposes exact and visual matches as separate search
                # types. The default "all" response is not a reliable source of
                # exact-match rows, so request both explicitly for every frame.
                for search_type,result_key,match_type in (
                    ('exact_matches','exact_matches','exact'),
                    ('visual_matches','visual_matches','similar'),
                ):
                    response=client.get('https://serpapi.com/search.json',params={
                        'engine':'google_lens','type':search_type,'image_id':image_id,
                        'safe':'active','hl':'en','api_key':key})
                    if response.status_code!=200:raise SearchUnavailable('Reverse search unavailable. Check provider quota or try again later.')
                    row=response.json()
                    for item in result_items(row,result_key)[:50]:
                        url=safe_url(item.get('link'))
                        if not url:continue
                        source=str(item.get('source','')).strip()[:128]
                        thumbnail=safe_url(item.get('thumbnail'))
                        host=(urlsplit(url).hostname or '').lower()
                        is_instagram=host=='instagram.com' or host.endswith('.instagram.com')
                        candidate={
                            'url':url,
                            'title':str(item.get('title','')).strip()[:256],
                            'source':source,
                            'kind':'exact_match' if match_type=='exact' else 'visually_similar',
                            'matchType':match_type,
                            'frames':[frame],
                            'verified':False,
                            'instagram':is_instagram,
                        }
                        if thumbnail:candidate['thumbnail']=thumbnail
                        existing=results.get(url)
                        if existing:
                            if frame not in existing['frames']:existing['frames'].append(frame)
                            if match_type=='exact':
                                existing['kind']='exact_match';existing['matchType']='exact'
                            existing['instagram']=existing.get('instagram',False) or is_instagram
                        else:results[url]=candidate
        ranked=sorted(results.values(),key=lambda item:(
            0 if item['matchType']=='exact' and item.get('instagram') else
            1 if item['matchType']=='exact' else
            2 if item.get('instagram') else 3,
            -len(item['frames']), item['url']))
        return ranked[:50]
    except (httpx.HTTPError,ValueError,KeyError,TypeError,AttributeError):
        raise SearchUnavailable('Web search did not return usable results. Try again later.') from None
