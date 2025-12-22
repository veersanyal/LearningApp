
from app import app

def verify_assets():
    print("Verifying UI assets...")
    with app.test_client() as client:
        # Check style.css
        response = client.get('/static/style.css')
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            # Check for Purdue Re-Branding elements
            expected_styles = [
                "background-color: #000000", # Deep Black
                "#D0B991", # Old Gold
                "#9D9796", # Silver
                ".sparkline-placeholder"
            ]
            
            missing = [s for s in expected_styles if s not in content]
            
            if not missing:
                print("SUCCESS: style.css contains all Purdue Brand elements!")
            else:
                print(f"FAILURE: Missing styles: {missing}")
                exit(1)
        else:
            print(f"FAILED: style.css returned {response.status_code}")

if __name__ == '__main__':
    verify_assets()
