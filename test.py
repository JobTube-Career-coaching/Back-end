#################################
#API TEST
#################################
from flask import Flask,render_template,request,jsonify
import requests
import json
app=Flask(__name__)
@app.route("/")
def index():
    labels = []
    labels2 = []
    data2 = []
    data3 = []
    labels3 = []
    data4 = []
    return render_template("api.html",
            dat=data2,
            dat2=data3,
            jobs=labels,
            wage=labels2,
            wlb=labels3,
            dat3=data4)
@app.route("/result")
def res():
    labels = []
    labels2 = []
    data2 = []
    data3 = []
    labels3 = []
    data4 = []
    i=0
    res=""
    key=request.args.get("Key")
    url="https://www.career.go.kr/cnet/front/openapi/jobs.json?apiKey={}&pageIndex={}".format(key,i)
    resp=requests.get(url)
    if(type(resp) is None):
        return "Req. Failed!, Result is None!"
    elif resp.status_code == 200:
        #return str(resp)
        data=resp.json()
        while i<=10:
            url="https://www.career.go.kr/cnet/front/openapi/jobs.json?apiKey={}&pageIndex={}".format(key,i)
            resp=requests.get(url)
            data=resp.json()
            i+=1
            # res+=str(data)
            for (j,k) in enumerate(data.items()):
                if(k[0].lower() not in ["count","pagesize","pageindex"]):
                    for l in k[1]: #['jobs']
                        if labels.count(l['aptit_name'])==0:
                            labels.append(str(l['aptit_name']))
                            data2.append(1)
                        else:
                            data2[labels.index(str(l['aptit_name']))]+=1
                        try:
                            if labels2.count(l['wage'])==0:
                                labels2.append(str(l['wage']))
                                data3.append(1)
                            else:
                                data3[labels2.index(str(l['wage']))]+=1
                        except:
                            pass
                        try:
                            if labels3.count(l['wlb'])==0:
                                labels3.append(str(l['wlb']))
                                data4.append(1)
                            else:
                                data4[labels3.index(str(l['wlb']))]+=1
                        except:
                            continue
                else:
                    continue
               
        # return res
        # Return the components to the HTML template 
        return render_template(
            template_name_or_list='api.html',
            dat=data2,
            dat2=data3,
            jobs=labels,
            wage=labels2,
            wlb=labels3,
            dat3=data4
        )
    else:
        return "Req. Failed!,Err:"+str(resp.status_code)
if __name__=="__main__":
    app.run(host="0.0.0.0",port=5004)