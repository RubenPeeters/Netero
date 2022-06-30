class RegionException(Exception):
    def __init__(self, current_server, accepted_servers):
        Exception.__init__(
            self, f"Server given is {current_server}, should be one of the following : `{'`, `'.join(accepted_servers)}`")
