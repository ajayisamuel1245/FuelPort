import requests
from decouple import config   #helps read your env variable

PAYSTACK_BASE_URL = "https://api.paystack.co"
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')
PAYSTACT_CALLBACK_URL = config('PAYSTACK_CALLBACK_URL', default = 'ttp://127.0.0.1:8000/paystack-success-redirect')



headers = {
    "Authorization" : f'Bearer {PAYSTACK_SECRET_KEY}',
    "Content-Type" : "application/json"
}

def initializePayment(email : str, amount : float, reference : str):
    
    #Amount must be in the smallest currency unit
    data = {
        "email" : email,
        "amount" : amount,
        "callback_url" : PAYSTACT_CALLBACK_URL,
        "reference" : reference
    }
    
    try : 
        response = requests.post(f'{PAYSTACK_BASE_URL}/transaction/initialize', json=data, headers=headers)
        if response.status_code == 200:
            res_data = response.json()
            authorization_url = res_data["data"]["authorization_url"]
            refrence =res_data["data"]["reference"]
            return {
                "success" : True,
                "payment_url" : authorization_url,
                "refrence" : refrence
            }
        else:
            print("Error:", response.json())
            return None
    except Exception as e:
        print(e)
        return None
    
def verifyPayment( reference : str):

    # Amount must be in the smallest currency unit (e.g., kobo for NGN, multiply by 100)
    try :
        response = requests.get(f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}', headers=headers)

        if response.status_code == 200:
            res_data = response.json()
            if res_data['data']['status'] == 'success':
                return {
                    'success': True,
                    'amount' : res_data['data']['amount'] 
                }
            else :
                return {
                    'success' :False
                }
        else:
            print("Error:", response.json())
            
            return None
    except Exception as e :
        print(e)
        return None