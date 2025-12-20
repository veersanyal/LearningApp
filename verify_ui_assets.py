
from app import app

def verify_assets():
    print("Verifying UI assets...")
    with app.test_client() as client:
        # Check style.css
        response = client.get('/static/style.css')
        if response.status_code == 200:
            content = response.data.decode('utf-8')
            # Check for new UI polish elements
            expected_styles = [
                "Brand Mesh", # Keep checking for this
                "linear-gradient(rgba(15, 23, 42, 0.4)", # Dark overlay check
                ".sparkline-placeholder", # KPI sparklines
                "border-radius: var(--card-radius)" # Standardized radius
            ]
            
            missing = [s for s in expected_styles if s not in content]
            
            if not missing:
                print("SUCCESS: style.css contains all new UI polish elements!")
            else:
                print(f"FAILURE: Missing styles: {missing}")
                exit(1)
        else:
            print(f"FAILED: style.css returned {response.status_code}")

if __name__ == '__main__':
    verify_assets()
