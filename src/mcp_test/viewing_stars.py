from mcp_test.positions import get_star_position

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
cached = requests_cache.CachedSession('nasa_cache',expire_after=3600)  # caches the photo for an hour
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
        "timezone": "Asia/Singapore"}
    responses = w_cached.get(url, params = params)
    return responses.json()


def get_stars_and_planets(city:str, state:str, country:str):
    """ Gets visible stars and planets for the given location that can be seen at the night and their
    respective constellations"""

    url = "https://spacecatalog.org/api/v1/visible"
    addy = [city, state, country]
    
    query_params = {
    "name": ', '.join(addy),
    "count": 1,          # Number of search results to return
    "language": "en",
    "format": "json"}

    response = cached.get(
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
    params = {
        "lat": lat,
        "lon": lon,
        "time": datetime.now(timezone.utc).isoformat()
    }
    response = w_cached.get(url,params=params)
    r = response.json()
    print(r)

    with open("src\\mcp_test\\objects.yml", "r") as f:
        data = yaml.safe_load(f)

    wanted = {key : set(values) for key,values in data.items()}
    dynamic_lists = {}

    for key in wanted.keys():
        dynamic_lists[key] = []
        for val in wanted[key]:
            for rep in r.get('objects',[]):

                if key.lower() == rep.get('category').lower() and val.lower() == rep.get('name').lower():
                    dynamic_lists[key].append(rep)
                    break

    # get the viewing time range at night for the stars
    position = get_star_position(dynamic_lists['star'][0], lat, lon)

    print(f"{dynamic_lists['star'][0]}, calculated altitude deg: {position[0]}, calculated azimuth deg: {position[1]}")

    




    


if __name__ == "__main__":
    get_stars_and_planets("Hyderabad", "Telangana", "india")


     
    

