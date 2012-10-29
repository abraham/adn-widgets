import sys, os, json, uuid, time, requests, bottle, urllib
from pymongo import Connection
from bottle import debug, route, run, get, post, delete, put, error, template, static_file, response, request, redirect
from urlparse import parse_qs

'''
Assets
'''
@get('/')
def get_slash():
    redirect('https://alpha.app.net/widgets')
    return 'hello world'

@get('/alpha.js')
def get_alpha():
    return static_file('alpha.js', root='src/js')
@get('/core.js')
def get_core():
    return static_file('core.js', root='src/js')
@get('/provider.js')
def get_provider():
    return static_file('provider.js', root='src/js')
@get('/easyXDM.debug.js')
def get_easyxdm():
    return static_file('easyXDM.debug.js', root='src/js')


@get('/style.css')
def get_style():
    return static_file('style.css', root='src/css')

@get('/xdm.html')
def get_test():
    return static_file('xdm.html', root='src/views')
@get('/test.html')
def get_test():
    return static_file('test.html', root='src/views')

'''
Routes
'''
@get('/oauth/authenticate')
def get_oauth_authenticate():
    url = 'https://alpha.app.net/oauth/authenticate'
    url += '?client_id=' + env('ADN_CLIENT_ID')
    url += '&redirect_uri=' + urllib.quote_plus(env('ADN_REDIRECT_URI') + '/oauth/callback')
    url += '&response_type=code'
    url += '&scope=' + urllib.quote_plus('basic stream write_post follow')
    redirect(url)

@get('/oauth/callback')
def get_oauth_authenticate():
    code = request.query.code
    if not code:
        return 'Something went wrong. Close window and try again.'
    response = exchange_access_token(code)
    if not response.status_code == 200:
        return 'Error from App.net: ' + access_token.get('error', 'Uknown error')
    
    profile = json.loads(response.content)
    profile['user_id'] = str(profile['user_id'])
    access_token = {'_id':generate_access_token(), 'expire':generate_timestamp() + 60 * 60 * 3, 'user_id': profile.get('user_id')}
    
    db = get_db()
    profile['_id'] = str(profile.get('user_id'))
    db.profiles.update({'_id': profile.get('user_id')}, profile, True)
    db.access_tokens.insert(access_token)
    return template('callback.tpl', {'access_token': access_token.get('_id')})

@get('/api/profile')
def get_api_profile():
    request.content_type = 'application/json'
    if not request.query.access_token:
        return return_authentication_required()
    db = get_db()
    profile = get_profile_by_access_token(db, request.query.access_token)
    if not profile:
        return return_invalid_authentication()
        
    url = 'https://alpha-api.app.net/stream/0/users/me'
    headers={'Authorization': 'Bearer ' + profile.get('access_token')}
    response = requests.get(url, headers=headers)
    if not response.status_code == 200:
        response = requests.get(url, headers=headers)
    # TODO: handle errors better
    return json.loads(response.content)['data']

@get('/api/following')
def get_api_following():
    request.content_type = 'application/json'
    if not request.query.access_token:
        return return_authentication_required()
    db = get_db()
    profile = get_profile_by_access_token(db, request.query.access_token)
    if not profile:
        return return_invalid_authentication()
        
    following = get_following(profile.get('access_token'))
    print 'friends', len(following), following
    # TODO: only return array
    return {'following': following}

@post('/api/follow')
def post_api_follow():
    request.content_type = 'application/json'
    if not request.forms.access_token:
        return return_authentication_required()
    if not request.forms.username:
        return return_parameters_required()
    db = get_db()
    profile = get_profile_by_access_token(db, request.forms.access_token)
    if not profile:
        return return_invalid_authentication()
    response = follow(profile, request.forms.username)
    if not response:
        request.status = 500
        return '{"status":"error","message":"Unable to follow"}'
    return response

@delete('/api/follow')
def delete_api_follow():
    request.content_type = 'application/json'
    if not request.forms.access_token:
        return return_authentication_required()
    if not request.forms.username:
        return return_parameters_required()
    db = get_db()
    profile = get_profile_by_access_token(db, request.forms.access_token)
    if not profile:
        return return_invalid_authentication()
    response = unfollow(profile, request.forms.username)
    if not response:
        request.status = 500
        return '{"status":"error","message":"Unable to unfollow"}'
    return response


'''
Functions
'''
def follow(profile, username):
    headers = {'Authorization': 'Bearer ' + profile.get('access_token')}
    url = 'https://alpha-api.app.net/stream/0/users/@' + username + '/follow'
    
    response = requests.post(url, headers=headers)
    if not response.status_code == 200:
        response = requests.post(url, headers=headers)
    if not response.status_code == 200:
        return False
    
    response = json.loads(response.content)
    return response['data']
    
def unfollow(profile, username):
    headers = {'Authorization': 'Bearer ' + profile.get('access_token')}
    url = 'https://alpha-api.app.net/stream/0/users/@' + username + '/follow'
    
    response = requests.delete(url, headers=headers)
    if not response.status_code == 200:
        response = requests.post(url, headers=headers)
    if not response.status_code == 200:
        return False
    
    response = json.loads(response.content)
    return response['data']

def exchange_access_token(code):
    print 'code', code
    payload = {
        'client_id': env('ADN_CLIENT_ID'),
        'client_secret': env('ADN_CLIENT_SECRET'),
        'grant_type': 'authorization_code',
        'redirect_uri': env('ADN_REDIRECT_URI') + '/oauth/callback',
        'code': str(code)
    }
    url = 'https://alpha.app.net/oauth/access_token'
    response = requests.post(url, data=payload)
    if not response.status_code == 200:
        response = requests.post(url, data=payload)
    return response

def get_following(access_token, following=[], before_id=False):
    headers = {'Authorization': 'Bearer ' + access_token}
    payload = {}
    url = 'https://alpha-api.app.net/stream/0/users/me/following'
    if before_id:
        payload['before_id'] = before_id
    
    response = requests.get(url, headers=headers, params=payload)
    if not response.status_code == 200:
        response = requests.get(url, headers=headers, params=payload)
    if not response.status_code == 200:
        return following
    
    response = json.loads(response.content)
    for profile in response['data']:
        print profile.get('username')
        following.append(profile.get('username'))
    if response['meta']['more']:
        following = get_following(access_token, following, response['meta']['min_id'])
    # print 'pre return', following
    return following

def get_profile_by_access_token(db, access_token):
    access_token = db.access_tokens.find_one({'_id': access_token})
    if not access_token:
        return False
    profile = db.profiles.find_one({'_id': access_token.get('user_id')})
    if not profile:
        return False
    print 'get_profile_by_access_token:profile', profile
    return profile
    
def return_authentication_required():
    request.status = 401
    return '{"status":"error","message":"Access_token is required"}'
def return_parameters_required():
    request.status = 400
    return '{"status":"error","message":"Missing required parameters"}'
def return_invalid_authentication():
    request.status = 401
    return '{"status":"error","message":"Invalid access_token"}'
    

'''
Utility functions
'''
def env(name, default=False):
    return os.environ.get(name, default)

def get_db():
    if not env('MONGOHQ_URL'):
        sys.exit('database env is missing')
    table = env('MONGOHQ_URL', '').split('/')[3]
    return Connection(env('MONGOHQ_URL'))[table]

def generate_access_token():
    return generate_uuid() + generate_uuid() + generate_uuid()
def generate_uuid():
    return str(uuid.uuid4())
def generate_timestamp():
    return int(time.time())
    
'''
Server
'''
bottle.TEMPLATE_PATH.append('./src/views/')

if env('DEBUG', False) == 'True':
    print '==================================='
    print '==RUNNING WITH DEBUG MODE ENABLED=='
    print '==================================='
    debug(mode=True)
run(host='0.0.0.0', port=int(env('PORT', 1234)), reloader=True)
