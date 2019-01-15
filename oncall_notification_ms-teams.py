'''
This script grabs all the names from oncall setup of any organization.
The admins of each team need to put the incoming-webhook url of the teams
channel in the slack channel or team email column of the team info.
This will then grab that webhook url and send a notification whenever
the shift changes. It checks the shifts on an hourly basis.
'''
#https://oncall_link/api/v0/teams

import time
import requests
import pymsteams

# retrieve details
#------------------------------------------------------------
resp = requests.get('oncall_link/api/v0/teams')
if resp.status_code != 200:
    print("Error: {}", resp.status_code)

teams = resp.json()

links=[]
for i in range(0,len(teams)):
    suffix=teams[i]
    ur="oncall_link/team/"
    a=ur+suffix
    links.append(a)

summary=[]
for i in range(0,len(teams)):
    suffix=teams[i]
    prefix="oncall_link/api/v0/teams/"
    suffix2="/summary"
    a=prefix+suffix+suffix2
    summary.append(a)


webhook=[]
for i in range(0,len(teams)):
    a="oncall_link/api/v0/teams/"
    suffix=teams[i]
    b=a+suffix
    resp = requests.get(b)
    data = resp.json()
    data2 = str(data)
    init = 0
    end = 0
    for i in range(0, len(data2)):
        if (data2[i] == "#"):
            init = i
            break
    init += 1
    for i in range(init + 1, len(data2)):
        if (data2[i] == "#"):
            end = i
            break

    webhook1=data2[init:end]
    if("#" not in data2):
        webhook1=False

    webhook.append(webhook1)


#------------------------------------------------------------


# send message
#------------------------------------------------------------
def send(webhookurl,link,messagestring):

    if (webhookurl != False and len(str(webhookurl)) > 2 and messagestring != "NULL"):
        # webhook url
        myTeamsMessage = pymsteams.connectorcard(webhookurl)
        myTeamsMessage.title("Oncall person")
        myTeamsMessage.text(messagestring)
        myTeamsMessage.addLinkButton("View OnCall", link)
        # send the message.
        myTeamsMessage.send()
#------------------------------------------------------------


# print details
#------------------------------------------------------------
def prints(webhookurl,link,messagestring):

    if (webhookurl != False and len(str(webhookurl)) > 2 and messagestring != "NULL"):
        print("Message: {}".format(messagestring))
        print("link: {}".format(link))
        print("Webhook: {}".format(webhookurl))
        print("\n")
#------------------------------------------------------------


# retrieve messages
#------------------------------------------------------------
def getmessage():

    messages = []
    for i in range(0, len(teams)):
        newdata = requests.get(summary[i])
        newdata2 = newdata.json()
        flag = 0
        flag1 = 0
        flag2 = 0
        if (newdata2):
            flag = 0
        else:
            flag = 1
            messagestring = "Null"

        if (flag == 0):
            if (newdata2.get('current').get('primary')):
                # current on-call
                full_name = newdata2.get('current').get('primary')[0].get('full_name')
                email = newdata2.get('current').get('primary')[0].get('user_contacts').get('email')
                call = newdata2.get('current').get('primary')[0].get('user_contacts').get('call')
                sms = newdata2.get('current').get('primary')[0].get('user_contacts').get('sms')
                starttime = newdata2.get('current').get('primary')[0].get('start')
                endtime = newdata2.get('current').get('primary')[0].get('end')
                start = time.strftime('%H:%M', time.localtime(starttime))
                end = time.strftime('%H:%M', time.localtime(endtime))
                flag1 = 1

            if (newdata2.get('next')):
                # next on-call
                full_name2 = newdata2.get('next').get('primary')[0].get('full_name')
                email2 = newdata2.get('next').get('primary')[0].get('user_contacts').get('email')
                call2 = newdata2.get('next').get('primary')[0].get('user_contacts').get('call')
                sms2 = newdata2.get('next').get('primary')[0].get('user_contacts').get('sms')
                starttime2 = newdata2.get('next').get('primary')[0].get('start')
                endtime2 = newdata2.get('next').get('primary')[0].get('end')
                start2 = time.strftime('%H:%M', time.localtime(starttime2))
                end2 = time.strftime('%H:%M', time.localtime(endtime2))
                dates = time.strftime('%D', time.localtime(starttime2))
                flag2 = 1

        for j in range(0, len(email)):
            if (email[j] == "@"):
                break
        teams_user = email[0:j]

        for k in range(0, len(email2)):
            if (email2[k] == "@"):
                break
        teams_user2 = email2[0:k]


        if(len(str(newdata2))<50):
            messagestring = "NULL"

        elif (flag == 0):
            if (flag1 == 1 and flag2 == 1):
                messagestring = "Today " + full_name.upper() + " is oncall for " + teams[i] + ", from " + start + " to " + end + ". Email- " + email + " , Teams Username- " + teams_user + ". And " + full_name2.upper() + " is next oncall for " + teams[i] + ", from " + start2 + " to " + end2 + " on (MM/DD/YY)" + dates + ". Email- " + email2 + " , Teams Username- " + teams_user2
            elif (flag1 == 0 and flag2 == 1):
                messagestring = full_name2.upper() + " is next oncall for " + teams[i] + ", from " + start2 + " to " + end2 + " on (MM/DD/YY)" + dates + ". Email- " + email2 + " , Teams Username- " + teams_user
            elif (flag1 == 1 and flag2 == 0):
                messagestring = "Today " + full_name.upper() + " is oncall for " + teams[i] + ", from " + start + " to " + end + ". Email- " + email + " , Teams Username- " + teams_user

        messages.append(messagestring)

    return(messages)

#------------------------------------------------------------

msg=getmessage()

# send messages once when the script is run
#------------------------------------------------------------
for x in range(0,len(teams)):
    send(webhook[x],links[x],msg[x])
#------------------------------------------------------------


# hourly executing loop to send notification if any change occur
#------------------------------------------------------------
while(1>0):
    time.sleep(3600)
    msgnew=getmessage()
    for y in range(0, len(teams)):
        if(msg[y]!=msgnew[y]):
            send(webhook[y],links[y],msgnew[y])
    msg=getmessage()
#------------------------------------------------------------
