
from app import app

def verify_assets():
    print("Verifying UI assets...")
    with app.test_client() as client:
        # Check style.css
        response = client.get('/static/style.css')
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            if "Brand Mesh" in content:
                print("SUCCESS: style.css contains 'Brand Mesh'")
            else:
                print("FAILED: style.css does not contain 'Brand Mesh'")
        else:
            print(f"FAILED: style.css returned {response.status_code}")

if __name__ == '__main__':
    verify_assets()
