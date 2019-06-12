from falcon import HTTP_201, HTTPError
from ujson import dumps as json_dumps
import requests
def on_get(req, resp, team_name):
    def grab_team_roster(team_name):
        team = team_name
        data_get = requests.get("localhost:8080/api/v0/teams/" + team)
        json_ob = data_get.json()
        roster_data = {}
        team_roster = []
        team_id=json_ob.get('id')
        if (json_ob.get('rosters').keys()):
            roster = json_ob.get('rosters').keys()
            for i in roster:
                rname = i
                user_data = json_ob.get('rosters').get(i).get('users')

                users = []
                for i in user_data:
                    u_name=i.get('name')
                    u_id=json_ob.get('users').get(u_name).get('id')
                    u_data={}
                    u_data[u_name]=u_id
                    users.append(u_data)
                roster_data[rname] = users
            team_roster.append(team_id)
            team_roster.append(roster_data)
            return (team_roster)

    data=[]
    data_grab=grab_team_roster(team_name)
    data.append(data_grab)
    #return(data)
    resp.body = json_dumps(data)
