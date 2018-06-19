from resources.lib.helpers import Error
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError

# define all the possible JSON-RPC methods, for each and every video type
JSONRPC_METHODS = {
    'movie': {
        'list': {
            'method': 'VideoLibrary.GetMovies', # JSON-RPC method
            'result_key': 'movies' # JSON data field to extract
        },
        'details': {
            'method': 'VideoLibrary.GetMovieDetails', # JSON-RPC method
            'result_key': 'moviedetails' # JSON data field to extract
        }
    },
    'set': {
        'details': {
            'method': 'VideoLibrary.GetMovieSetDetails', # JSON-RPC method
            'result_key': 'setdetails' # JSON data field to extract
        }
    }
}

class LibraryError(Error):
    pass

# get all entries from the library for the given video_type
def get_list(video_type, **kwargs):
    try:
        method = JSONRPC_METHODS[video_type]['list']['method']
        result_key = JSONRPC_METHODS[video_type]['list']['result_key']
        return exec_jsonrpc(method, **kwargs)[result_key]
    except KeyError as e:
        raise LibraryError('cannot retrieve list of %ss: invalid key for BaseTask.JSONRPC_METHODS' % video_type, e)
    except JSONRPCError as e:
        raise LibraryError('Kodi JSON-RPC error: %s' % str(e), e)

# get details for a given library entry
def get_details(video_type, video_id, **kwargs):
    try:
        method = JSONRPC_METHODS[video_type]['details']['method']
        result_key = JSONRPC_METHODS[video_type]['details']['result_key']
        # inject the video ID in the arguments; key label is based on the video_type (+'id')
        kwargs[video_type + 'id'] = video_id
        # perform the JSON-RPC call
        return exec_jsonrpc(method, **kwargs)[result_key]
    except KeyError as e:
        raise LibraryError('cannot retrieve details for %s #%d: invalid key for BaseTask.JSONRPC_METHODS' % (video_type, video_id), e)
    except JSONRPCError as e:
        raise LibraryError('Kodi JSON-RPC error: %s' % str(e), e)
