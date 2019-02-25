import pymsteams
import logging
from oncall.constants import TEAMS_SUPPORT


class teams_messenger(object):
    supports = frozenset([TEAMS_SUPPORT])

    def __init__(self, config):
        self.webhook = config['webhook']

    def send(self, message):
        heading = message.get("subject")
        final_message = "User: " + message.get("user") + " Message: " + message.get("body")

        try:
            myTeamsMessage = pymsteams.connectorcard(self.webhook)
            myTeamsMessage.title(str(heading))
            myTeamsMessage.text(str(final_message))
            myTeamsMessage.send()
        except:
            logging.info("An issue occured while sending message to teams messenger")
