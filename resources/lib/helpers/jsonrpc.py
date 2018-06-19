import xbmc
import json
from resources.lib.helpers import addon_name, addon_icon, Error
from resources.lib.helpers.log import log

### JSON-RPC related helpers
class JSONRPCError(Error):
    def __init__(self, method, err_msg, command, ex):
        super(self.__class__, self).__init__('error executing %s: %s - command was: %s' % (method, str(err_msg), str(command)), ex)
        self.method = method
        self.command = command

def exec_jsonrpc(method, id='unknown', **kwargs):
    command = {
        'jsonrpc': '2.0',
        'id': id,
        'method': method
    }

    # wrap additional args in params if applicable
    if kwargs:
        command['params'] = kwargs

    # perfom the actual JSON-RPC call
    log.debug('JSON-RPC > executing: %s' % method)
    response = json.loads(xbmc.executeJSONRPC(json.dumps(command)))

    if response:
        if 'error' in response:
            raise JSONRPCError(method, response['error'], command)
        else:
            return response['result']
    else:
        return None

def notify(message, title = ''):
    exec_jsonrpc('GUI.ShowNotification', title = title if (title) else addon_name, message = message, image = addon_icon)
