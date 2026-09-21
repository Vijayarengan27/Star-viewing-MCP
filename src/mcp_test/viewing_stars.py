from mcp_test.positions import get_star_position, local_sidereal_and_isotime_calc

import os, sys
from mcp.server import MCPServer
import requests
from datetime import datetime, timedelta, time, timezone

from dotenv import load_dotenv
import base64
import requests_cache
import yaml





load_dotenv()

mcp = MCPServer("nasa_test")
cached = requests_cache.CachedSession('nasa_cache',expire_after=216000)  # caches the photo for a day
w_cached = requests_cache.CachedSession('weather_cache', expire_after=900)  # cache for weather info
IST_zone = timezone(timedelta(hours=5, minutes=30))  # helpful in calculating the indian time 

def _get_image_of_the_day(date):

    """Gets the image of the day from NASA """

    query_params = {'date':date,
                    'api_key': os.getenv("API_KEY")}
    response = cached.get(url="https://api.nasa.gov/planetary/apod",
                            params=query_params)
    remaining = response.headers.get("X-RateLimit-Remaining")
    print(f"{remaining} attempts left",file=sys.stderr)

    return response.json()

@mcp.tool()
def show_image_of_the_day():

    """Displays the image url or plays the mp4 file"""

    response = _get_image_of_the_day(datetime.date.today().isoformat())

    result = [{"Title": response["title"], "Explanation": response["explanation"]}]

    if response["media_type"] == "image":
        image_response = requests.get(response['url'])
        base64_data = base64.b64encode(image_response.content).decode("utf-8")
        mime = image_response.headers.get('content-type')
    
        # Return using the image content type
        result.append(
            {
                "type": "image",
                "data": base64_data,
                "mimeType": mime
            })
    else:
        result.append(
        {
            "type": "text",
            "text": f"Here is the video of the day: [Play Video]({response['url']})"
        })
    return result


def _get_location(city:str, state:str, country:str):
    """Gets the given location as latitude and longitude"""

    addy = [city, state, country]

    query_params = {
    "name": ', '.join(addy),
    "count": 1,          # Number of search results to return
    "language": "en",
    "format": "json"}

    response = w_cached.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params=query_params
    )

    if response.status_code == 200:
        data = response.json()
        
    # Extract results array
    results = data.get("results", [])
    for spot in results:  # just running for one as of now
        lat = spot.get("latitude")
        lon = spot.get("longitude")

    return lat, lon
        
@mcp.tool()
def get_weather(city:str, state:str, country:str):
    """ Gets the hourly weather forecast of the given location"""
    
    lat, lon = _get_location(city=city, state=state, country=country)  # hardcoded rn, but need to make it dynamic
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["uv_index_max", "sunrise", "sunset", "moonrise", "moonset"],
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "rain", "precipitation"],
        "timezone": "auto"}
    responses = w_cached.get(url, params = params)
    return responses.json()

def get_cloud_cover(lat: float , lon: float , sunset: datetime, sunrise: datetime):
    # get the latitude and longitude of the observer location

    # need the sunset and sunrise of the current day
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloud_cover",
        "timezone": "auto"
    }

    response = w_cached.get(url, params = params)
    data = response.json()

    dict = {(datetime.fromisoformat(x).day,datetime.fromisoformat(x).hour) : cc for x,cc in zip(data['hourly']['time'], data['hourly']['cloud_cover']) }

    start = (sunset.day, sunset.hour)
    end = (sunrise.day, sunrise.hour)

    cloud_cover = {key:value for key,value in dict.items() if start <= key <= end}
    return cloud_cover


def get_star_hashmaps(lat:float, lon:float, sunset: datetime.isoformat) -> list[dict]:
    """ Runs the api for the favorite stars provided in the objects.yml file and returns the
    json response from the requests"""

    star_list = []

    with open("src\\mcp_test\\objects.yml", "r") as f:
            data = yaml.safe_load(f)
    
    wanted = {key : set(values) for key,values in data.items()}
    params = {
            "lat": lat,
            "lon": lon,
            "time": sunset
        } 

    stars = [star for star_set in wanted.values() for star in star_set]
    for slug in stars:
        print(slug)
        url = f"https://spacecatalog.org/api/v1/objects/{slug.lower()}"
        response = w_cached.get(url,params=params)
        r = response.json()
        star_list.append(r)
    return star_list






def get_stars_and_planets(city:str, state:str, country:str):
    """ Gets visible stars and planets for the given location that can be seen at the night and their
    respective constellations"""

    # get the latitude and longitude of the observer location
    lat, lon = _get_location(city, state, country)

    # need the sunset and sunrise of the current day
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["sunrise", "sunset"],
        "timezone": "auto"}

    response = w_cached.get(url, params = params)
    data = response.json()

    # process the sunset and sunsrise from json output, that is in iso8601 format
    sunset = data['daily']['sunset'][0]  # today's sunset
    sunrise = data['daily']['sunrise'][1]  # tomorrow's sunrise
    print(f"data: {data}")

    # get the visible objects in the night sky at the given time
    dynamic_list = get_star_hashmaps(lat, lon, sunset)
    

    # convert sunset and sunrise to datetime objects
    sunrise = datetime.fromisoformat(sunrise)
    sunset = datetime.fromisoformat(sunset)

    

    # get cloud cover for the given time range
    cloud_cover = get_cloud_cover(lat, lon, sunset, sunrise)

    # get the local sidereal time lists and isoformat time for 15 minute intervals from sunset to sunrise
    time_list, lst_list = local_sidereal_and_isotime_calc(sunset, sunrise, lon)

    # get the viewing time range at night for the stars
    position = get_star_position(dynamic_list, lat, lon, cloud_cover, time_list, lst_list)
    
    return position

    




    


if __name__ == "__main__":
    print(get_stars_and_planets("Tiruchirappalli", "Tamil nadu", "india"))
    # get_cloud_cover("Tiruchirappalli", "Tamil nadu", "india", datetime.now(), datetime.now() + timedelta(hours=12))


     
    

