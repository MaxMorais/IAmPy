
class ODict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __getattr__(self, name):
        return self.get(name)

    def __getitem__(self, name):
        return self.get(name)



class Observable(ODict):
    def __init__(self):
        self._observable = {
            'is_hot': {},
            'event_queue': {},
            'listeners': {},
            'once_listeners': {}
        }

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        self.trigger('before_change', 
            doc = self,
            fieldname = key,
            new_value = value
        )
        old = self[key]
        self[key] = value
        self.trigger('after_change', {
            doc = self,
            fieldname = key,
            old_value = old,
            new_value = value
        })

    def on(self, event, listener):
        self._add_listener('listeners', event, listener)
        if hasattr(self._observable, 'socket_client'):
            self._observable.socket_client.on(event, listener)
        
    def off(self, event, listener):
        for _type in ('listeners', 'once_listeners'):
            if event in self._observable[_type] and listener in self._observable[_type][event]:
                self._observable[_type][event].remove(listener)
        
    def once(self, event, listener):
        self._add_listener('once_listeners', event, listener)

    def trigger(self, event,throttle = False, **params):
        if throttle:
            if self._throttled(event, throttle, **params): return
        self._execute_triggers(event, **params)

    def _execute_triggers(self, event, params):
        response = self._trigger_event('listeners', event, **params)
        if not response: return

        response = self._trigger_event('once_listeners', event, **params)

        # emit via socket
        if hasattr(self._observable, 'socket_server'):
            self._observable.socket_server.trigger(event, params)

        # clear once-listeners
        self._observable['once_listeners'].pop(event, None)

    def clear_listeners(self):
        self._observable.update({'listeners': {}, 'once_listeners': {}})

    def bind_socket_client(self, socket):
        self._observable.socket_client = socket
    
    def bind_socket_server(self, socket):
        self._observable.socket_server = socket

    def _throttled(self, event, throttle, **params):
        from threading import Timer
        from functools import delay

        def delay(delay=0.):
            """
            Decorator for delaying the execution of a function for a while.
            """
            def wrap(f):
                @wraps(f)
                def delayed(*args, **kwargs):
                    Timer(delay, f, args=args, kwargs=kwargs).start()
                return delayed
            return wrap

        if event in self._observable['is_hot']:
            # hot, add to queue
            if event not in self._observable['event_queue']:
                self._observable['event_queue'][event] = []
            self._observable['event_queue'][event].append(params)
            return True
        
        self._observable['is_hot'][event] = True
        
        @delay
        def throttled():
            self._observable['is_hot'][event] = False

            _queued_params = self._observable.event_queue[event]
            self._observable[event_queue].pop(event, None)
            self._execute_triggers(event, _queued_params)

        throttled()

        return False

    