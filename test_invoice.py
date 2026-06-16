from app import app

print("Initializing Flask test client...")
with app.test_client() as client:
    print("Simulating admin login session...")
    with client.session_transaction() as sess:
        sess['admin_id'] = 1
        sess['role'] = 'admin'
        sess['username'] = 'admin'
        
    print("Testing GET request to /order/7/invoice...")
    response = client.get('/order/7/invoice')
    print("Response Status Code:", response.status_code)
    
    if response.status_code == 200:
        print("Success! Invoice route works perfectly.")
        # Print a snippet of the response HTML
        html = response.data.decode('utf-8')
        print("Invoice title present:", "INV-0007" in html)
    else:
        print("Error detected! Response body:")
        print(response.data.decode('utf-8'))
