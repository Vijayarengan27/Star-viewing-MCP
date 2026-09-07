import requests

query_params = {
    "name": "Hyderabad, Telangana, India",
    "count": 1,          # Number of search results to return
    "language": "en",
    "format": "json"
}

response = requests.get(
    "https://geocoding-api.open-meteo.com/v1/search",
    params=query_params
)

if response.status_code == 200:
    data = response.json()
    
    # Extract results array
    results = data.get("results", [])
    
    for spot in results:
        name = spot.get("name")
        country = spot.get("country")
        admin1 = spot.get("admin1")  # State/Region
        lat = spot.get("latitude")
        lon = spot.get("longitude")
        
        print(f"Location: {name}, {admin1}, {country}")
        print(f"Coordinates: Lat {lat}, Lon {lon}")
        print("-" * 30)
else:
    print(f"Error {response.status_code}: {response.text}")