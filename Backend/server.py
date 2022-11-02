from flask import Flask
from flask import request
from flask import jsonify
from flask_api import status
import requests

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

app = Flask(__name__)

# rules for the rate limiter
# Initial bucket count is 4 tokens. 
# Refill rate is 2 tokens per 20 seconds 
# The endpoint can be accessed 4 times per 20 seconds
myRefillRate = 2
myBucketSize = 4
myUserDictArray = []


# refills the userObjBucket every 20 secons
def my_refiller():
    global myRefillRate , myUserDictArray
    if myUserDictArray != []:
        for userObj in myUserDictArray :
            if(userObj['currentTokenCount'] <= 2):
                if(userObj['currentTokenCount'] == -1):
                    userObj['currentTokenCount'] = myRefillRate      
                else:
                    userObj['currentTokenCount'] += myRefillRate - 1
                print('refilling bucket')
            else:
                print('bucket has >2 tokens')

sched = BackgroundScheduler(daemon=True)
sched.add_job(my_refiller,'interval',seconds=20)
sched.start()



def my_rate_limiter(clientIp , isPresent):
    global myBucketSize;
    myResponse = {}

    if not isPresent :
        myUserObj = {
        'client_ip' : clientIp,
        'currentTokenCount' : myBucketSize-1    
        }
        myUserDictArray.append(myUserObj)
        print('Adding user to array')
        myResponse['currentTokenCount'] = myBucketSize-1
        myResponse['statusCode'] = 200

    else : 
        # find user and update his token count
        response =  [user for user in myUserDictArray if user["client_ip"] == clientIp]
        index = myUserDictArray.index(response[0])
        tempObj = response[0]
        if(tempObj['currentTokenCount'] >= 0) :
            tempObj['currentTokenCount'] -= 1
        myUserDictArray[index] = tempObj

        myResponse['currentTokenCount'] = tempObj['currentTokenCount']
        myResponse['statusCode'] = 200 if tempObj['currentTokenCount'] >= 0 else 429

    return myResponse


def get_client_ip():
    r = requests.get('https://api.db-ip.com/v2/free/self')     # 1,000 requests per day
    respFromDbIp = r.json()
    return respFromDbIp

def checkIfUserPresentInHashArray(clientIp):
    response =  [user for user in myUserDictArray if user["client_ip"] == clientIp]
    return False if response == [] else True

# middleware
# @app.before_request
def before_request_func(): 
    if(request.path == '/'):
        clientIp = get_client_ip()
        isPresent = False if myUserDictArray==[]  else checkIfUserPresentInHashArray(clientIp)            # a if condition else b
        resposeFromRateLimiter = my_rate_limiter(clientIp , isPresent)
        return resposeFromRateLimiter


@app.route("/")
def hello_world():
    responseFromRateLimiter = before_request_func()
    if responseFromRateLimiter['statusCode'] == 200 : 
        responseFromRateLimiter['message']  = 'Request Successful'
        return responseFromRateLimiter,status.HTTP_200_OK
    else :
        responseFromRateLimiter['message']  = 'You are rate limited'
        return responseFromRateLimiter,status.HTTP_429_TOO_MANY_REQUESTS


if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host='0.0.0.0', port=80)
