
class ODict(dict):
    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        return None
        
    def __getattr__(self, name):
        return self[name]
        
    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f'No such attribute: {name}')

class Observable(ODict):
    def __init__(self, *args, **kwargs):
        kwargs['_observable'] = ODict(
            is_hot = ODict(),
            event_queue = ODict(),
            listeners = ODict(),
            once_listeners = ODict()
        )

        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        self.trigger('before_change', 
            doc = self,
            fieldname = key,
            new_value = value
        )
        old = self.get(key)
        super().__setitem__(key, value)
        self.trigger('after_change', 
            doc = self,
            fieldname = key,
            old_value = old,
            new_value = value
        )

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

    def trigger(self, event, throttle = False, **params):
        if throttle:
            if self._throttled(event, throttle, **params): return
        self._execute_triggers(event, **params)

    def _execute_triggers(self, event, **params):
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
        from functools import wraps

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

        if event in self._observable.is_hot:
            # hot, add to queue
            if event not in self._observable.event_queue:
                self._observable.event_queue[event] = []
            self._observable.event_queue[event].append(params)
            return True
        
        self._observable.is_hot[event] = True
        
        @delay()
        def throttled():
            self._observable.is_hot[event] = False

            _queued_params = self._observable.event_queue[event]
            self._observable[event_queue].pop(event, None)
            self._execute_triggers(event, _queued_params)

        throttled()

        return False
    
    def _add_listener(self, type_, event, listener):
        if type_ not in self._observable:
            self._observable[type_] = {}
        if event not in self._observable[type_]:
            self._observable[type_][event] = []
        self._observable[type_][event].append(listener)

    def _trigger_event(self, type_, event, **params):
        if event in self._observable[type_]:
            for listener in self._observable[_type][event]:
                listener(**params)