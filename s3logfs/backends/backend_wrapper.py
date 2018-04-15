from abc import ABC

class BackendWrapper(ABC):
    '''
    Abstract base class that wraps a backend and forwards any undefined method
    calls to it.
    '''

    def __init__(self, backend):
        self._backend = backend

    def __getattr__(self, name):
        '''
        This gets called when an attribute "name" was looked up on self but was
        not found. We then "forward" the lookup to the backend.
        '''
        return getattr(self._backend, name)
