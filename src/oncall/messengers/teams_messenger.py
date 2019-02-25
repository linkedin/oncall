import pymsteams
from oncall.constants import TEAMS_SUPPORT

class teams_messenger(object):
    supports = frozenset([TEAMS_SUPPORT])
    
    def __init__(self, config):
        self.webhook = config['webhook']

    def send(self, message):
        heading=message.get("subject")
        final_message="User: "+message.get("user")+"\nMessage: "+message.get("body")
        webhook=self.webhook
        myTeamsMessage = pymsteams.connectorcard(webhook)
        myTeamsMessage.title(str(heading))
        myTeamsMessage.text(str(final_message))
        # send the message.
        myTeamsMessage.send()

        #if error
        #logger.info("Error while connecting to teams_messenger")
