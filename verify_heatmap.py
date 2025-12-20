
from app import app, get_db
import json

def test_heatmap_api():
    print("Testing /api/heatmap endpoint...")
    
    with app.test_client() as client:
        # Test default filter (now)
        response = client.get('/api/heatmap')
        if response.status_code != 200:
            print(f"FAILED: Status code {response.status_code}")
            print(f"Error details: {response.data}")
            return
            
        data = json.loads(response.data)
        if 'locations' not in data:
            print("FAILED: 'locations' key missing in response")
            return
            
        locations = data['locations']
        print(f"SUCCESS: Retrieved {len(locations)} locations")
        
        # Verify content
        for loc in locations:
            print(f" - {loc['name']}: {loc['students']} students")
            
        # Test with 24h filter
        response = client.get('/api/heatmap?filter=24h')
        data = json.loads(response.data)
        print(f"SUCCESS (24h): Retrieved {len(data['locations'])} locations")

if __name__ == '__main__':
    test_heatmap_api()
