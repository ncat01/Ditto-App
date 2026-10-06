"""Google Vision Web Detection on original images or five sampled video frames.
Search returns unverified links; it neither fetches arbitrary URLs nor asserts infringement.
"""
import base64, io
from urllib.parse import urlsplit
import cv2, httpx
from PIL import Image, ImageOps
from app.config import get_settings

class SearchUnavailable(RuntimeError): pass

def query_images(path,kind):
    images=[]
    if kind=='video':
        capture=cv2.VideoCapture(str(path))
        try:
            if not capture.isOpened():raise ValueError('Video cannot be decoded')
            count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            for i in range(5):
                capture.set(cv2.CAP_PROP_POS_FRAMES,int(max(count-1,0)*i/4))
                ok,frame=capture.read()
                if not ok:raise ValueError('Video frame cannot be decoded')
                images.append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
        finally:capture.release()
    else:
        with Image.open(path) as source:
            if source.width*source.height>40000000:raise ValueError('Image is too large')
            images.append(ImageOps.exif_transpose(source).convert('RGB'))
    encoded=[]
    for image in images:
        image.thumbnail((1280,1280));buffer=io.BytesIO();image.convert('RGB').save(buffer,format='JPEG',quality=85)
        encoded.append(base64.b64encode(buffer.getvalue()).decode())
    return encoded

def safe_url(value):
    if not isinstance(value,str) or len(value)>2048:return None
    try:
        uri=urlsplit(value)
        if uri.scheme not in ('http','https') or not uri.hostname or uri.username or uri.password:return None
        return value
    except ValueError:return None

def search(images):
    key=get_settings().google_cloud_api_key.get_secret_value()
    if not key:raise SearchUnavailable('Web search is not configured. Original uploads and local comparison remain available.')
    payload={'requests':[{'image':{'content':image},'features':[{'type':'WEB_DETECTION','maxResults':10}]} for image in images]}
    try:
        with httpx.Client(timeout=45,follow_redirects=False) as client:
            response=client.post('https://vision.googleapis.com/v1/images:annotate',headers={'X-Goog-Api-Key':key},json=payload)
        if response.status_code!=200:raise SearchUnavailable('Web search unavailable. Check the operator?s provider configuration and quota.')
        rows=response.json()['responses']
        if len(rows)!=len(images) or any('error' in row for row in rows):raise ValueError()
        results={}
        for frame,row in enumerate(rows):
            web=row.get('webDetection',{})
            for group,kind in [('pagesWithMatchingImages','matching_page'),('fullMatchingImages','image_match'),('partialMatchingImages','partial_image'),('visuallySimilarImages','visually_similar')]:
                for item in web.get(group,[])[:10]:
                    url=safe_url(item.get('url'))
                    if not url:continue
                    if url not in results:results[url]={'url':url,'title':str(item.get('pageTitle',''))[:256],'kind':kind,'frames':[],'verified':False}
                    if frame not in results[url]['frames']:results[url]['frames'].append(frame)
        return list(results.values())[:50]
    except (httpx.HTTPError,ValueError,KeyError,TypeError,AttributeError):
        raise SearchUnavailable('Web search did not return usable results. Try again later.') from None
