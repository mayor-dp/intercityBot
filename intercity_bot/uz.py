import aiohttp
import aiofiles
import json
import time
import random
import os
from urllib.parse import urlencode
from intercity_bot.user import User

API_URL = "https://booking.uz.gov.ua/"



class Station:
    def __init__(self, title, id):
        self.title = title
        self.id = id

    def toDict(self):
        return {'title': self.title, 'id': self.id}


class CaptchaException(Exception):
    pass


class UnknownException(Exception):
    pass


async def api_request(method: str, parameters: dict, type: str, user: User, lang: str = "ru"):
    cookies = {'_gv_sessid': user.cookie_session}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        if type == 'get':
            url = "{}{}/{}?{}".format(API_URL, lang, method, urlencode(parameters))
            async with session.get(url) as response:
                if '_gv_sessid' in response.cookies:
                    if user.cookie_session != response.cookies['_gv_sessid'].value:
                        user.update_cookie_session(response.cookies['_gv_sessid'].value)
                
                return json.loads(await response.text())
        elif type == 'post':
            url = "{}{}/{}".format(API_URL, lang, method)
            async with session.post(url) as response:
                if '_gv_sessid' in response.cookies:
                    if user.cookie_session != response.cookies['_gv_sessid'].value:
                        user.update_cookie_session(response.cookies['_gv_sessid'].value)

                return json.loads(await response.text())


async def search_stations(user: User, search_request: str):
    result = await api_request('train_search/station/', {'term': search_request}, 'get', user)
    return list(map(lambda station: Station(station['title'], station['value']), result))


async def search_trains(user: User, station_from_id: int, station_to_id: int, date: str, time: str = '00:00', captcha: str = None):
    parameters = {'from': station_from_id, 'to': station_to_id, 'date': date, 'time': time}
    if captcha is str:
        parameters['captcha'] = captcha

    result = await api_request('train_search/', parameters, 'get', user)

    if 'error' in result:
        if result['error'] == 1:
            raise CaptchaException()
        else:
            raise UnknownException()

    return result


async def get_captcha(user: User):
    cookies = {'_gv_sessid': user.cookie_session}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.get("{}{}".format(API_URL, 'captcha/')) as response:
            random.seed(time.time())
            script_dir = os.path.dirname(__file__)
            filename = "{}/captcha/{}.gif".format(script_dir, random.randint(0, 999_999_999))

            async with aiofiles.open(filename, "wb") as file:
                await file.write(await response.read())
                await file.close()

            return filename