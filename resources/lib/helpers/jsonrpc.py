import xbmc
import json
from resources.lib.helpers import addon_name
from resources.lib.helpers.log import log
from resources.lib.helpers.exceptions import Error

### JSON-RPC related helpers
class JSONRPCError(Error):
    def __init__(self, method, err, command):
        self.method = method
        self.error = err
        self.command = command
        super(self.__class__, self).__init__('JSON-RPC error executing %s: %s - command was: %s' % (method, str(err), str(command)))

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
    log.debug('executing JSON-RPC call: %s' % method)
    response = json.loads(xbmc.executeJSONRPC(json.dumps(command)))

    if response:
        if 'error' in response:
            raise JSONRPCError(method, response['error'], command)
        else:
            return response['result']
    else:
        return None

def notify(message):
    exec_jsonrpc('GUI.ShowNotification', title=addon_name, message=message)
