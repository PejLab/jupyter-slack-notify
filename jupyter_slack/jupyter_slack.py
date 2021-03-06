import os
import time
import warnings
import requests
import traceback
from IPython.core import magic_arguments
from IPython.core.magics import ExecutionMagics
from IPython.core.magic import cell_magic, magics_class
from os.path import expanduser

def notify_self(message):
   
    #A file called ~/.slack_webhook_jupyterhub is in every user's home folder
    #where the slack webhook is stored. 
    homedir = expanduser("~")
    f = open(homedir + "/.slack_webhook_jupyterhub",'r')
    slack_webhook_url = f.readlines()
    slack_webhook_url = slack_webhook_url[0].replace("\n","")
    
    if slack_webhook_url is not None:
        r = requests.post(slack_webhook_url, json={"text": message})
        return r.text, message
    else:
        slack_token = os.getenv("SLACK_TOKEN")
        slack_id = os.getenv("SLACK_ID")
        if slack_token is not None and slack_id is not None:
            warnings.warn("Slack tokens are a legacy feature and may be deprecated at any time: "
                          "Consider moving to webhooks (see https://api.slack.com/messaging/webhooks) "
                          "for more details")
            parameters = {
                "token": slack_token,
                "channel": "@" + slack_id,
                "text": message
            }
            r = requests.post("https://slack.com/api/chat.postMessage", params=parameters)
            return r.text, message
        else:
            raise ValueError("Either $SLACK_WEBHOOK_URL must be set "
                             "(see https://api.slack.com/messaging/webhooks) "
                             "or both $SLACK_TOKEN and $SLACK_ID must be set "
                             "(see https://api.slack.com/custom-integrations/legacy-tokens)")

class Monitor:
    def __init__(self, msg, time=False,
            send_full_traceback=False, send_on_start=False,
            start_prefix="Started", end_prefix="Finished",
            err_prefix="Error while"):
        self.msg = msg
        self.time = time
        self.send_on_start = send_on_start
        self.send_full_traceback = send_full_traceback
        self.start_prefix = start_prefix
        self.end_prefix = end_prefix
        self.err_prefix = err_prefix

    @staticmethod
    def construct_time_mess(elapsed):
        day = elapsed // (24 * 3600)
        elapsed = elapsed % (24 * 3600)
        hour = elapsed // 3600
        elapsed %= 3600
        minutes = elapsed // 60
        elapsed %= 60
        seconds = round(elapsed, 1)
        time_mess = ""
        if day > 0:
            time_mess += " {} days".format(day)
        if hour > 0:
            time_mess += " {} hours ".format(hour)
        if minutes > 0:
            time_mess += " {} minutes".format(minutes)
        if seconds > 0:
            time_mess += " {} seconds".format(seconds)
        return time_mess

    def __enter__(self):
        self._start = time.time()
        if self.send_on_start: notify_self("{} {}".format(self.start_prefix, self.msg))
        return self

    def __exit__(self, exception_type, exception_value, tb):
        if exception_value is None:
            if self.time:
                elapsed = time.time() - self._start
                msg = "{} {} in {}".format(self.end_prefix, self.msg, self.construct_time_mess(elapsed))
            else: msg = "{} {}".format(self.end_prefix, self.msg)
            notify_self(msg)
        else:
            if self.send_full_traceback:
                trace = ''.join(traceback.format_exception(exception_type, exception_value, tb)).strip()
            else:
                trace = "{!r}".format(exception_value)
            msg = "{} {}'\n```\n{}\n```".format(self.err_prefix, self.msg, trace)
            notify_self(msg)
            raise exception_value.with_traceback(tb)

@magics_class
class MessengerMagics(ExecutionMagics):

    def __init__(self, shell):
        super().__init__(shell)

    @cell_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument("message", type=str)
    @magic_arguments.argument("--time", "-t", action="store_true")
    def notify(self, line="", cell=None):
        args = magic_arguments.parse_argstring(self.notify, line)
        mess = args.message.replace("\"", "")
        with Monitor(mess, time=args.time):
            self.shell.ex(cell)
