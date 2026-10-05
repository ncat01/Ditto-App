"""Run on the operator's Codespaces terminal, not through the public API."""
import sys,json,getpass,os
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.providers.instagram import InstagramReader,InstagramUnavailable
from app.services.instagram_binding import BINDING_FILE,token_digest
email=input('Ditto account email (use this in Connected test): ').strip()
password=getpass.getpass('Ditto password (hidden): ')
create='--create' in sys.argv
with httpx.Client(base_url='http://127.0.0.1:8010',timeout=30,follow_redirects=False) as client:
    r=client.post('/api/auth/signup' if create else '/api/auth/login',json={'email':email,'password':password})
    if r.status_code not in (200,201):raise SystemExit('Ditto sign-in failed. Use an existing account, or --create for a new account.')
    session=r.json()
    try:
        profile=InstagramReader().profile()
        BINDING_FILE.parent.mkdir(exist_ok=True)
        temp=BINDING_FILE.with_suffix('.tmp')
        temp.write_text(json.dumps({'ditto_user_id':session['user']['id'],'instagram_user_id':profile.user_id,'token_digest':token_digest()}))
        os.chmod(temp,0o600);temp.replace(BINDING_FILE)
        print('Instagram linked to this Ditto account. Other Ditto accounts cannot access it.')
    except InstagramUnavailable as exc:raise SystemExit(str(exc))
    finally:client.post('/api/auth/logout',headers={'Authorization':'Bearer '+session['token']})
