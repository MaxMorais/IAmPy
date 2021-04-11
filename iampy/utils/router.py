import re
from .observable import Observable, ODict

class Router(observable):
    def __init__(self):
        super()
        self.last_route = None
        self.current_page = None
        self.static_routes = []
        self.dynamic_routes = []

    def add(self, route, handler):
        page = ODict(
            handler = handler,
            route = route
            # re.findall(":([^/]+)", "/todo/:name/:place")
            param_keys = re.findall(':([^/]+)', route)
        )

        if page.param_keys:
            # make expression
            #  re.sub(r'\/:([^/]+)', r'\/([^/]+)', r'/todo/:name/:place')
            page.depth = len(route.split('/'))
            page.expression =  re.sub(r'\/:([^/]+)', r'\/([^/]+)', route)
            self.dynamic_routes.append(page)
            self.dynamic_routes.sort(key=lambda o: o.depth or len(o.param_keys) or len(a.route))
        else:
            self.static_routes.append(page)
            self.static_routes.sort(key=lambda o: len(a.route))
        
    def listen(self):
        try:
            from browser import window, bind

            @bind('hashchange', window)
            def callback(event):
                route = self.get_route_string()
                if self.last_route != route:
                    self.show(route)
            
        except ImportError as e:
            pass
    
    @property
    def route(self):
        route = self.get_route_string()
        if route:
            return route.split('/')
        return []

    @route.setter
    def route(self, parts):
        route = parts.join('/')

        # setting this first, doesn't trigger show via
        # hashchage, since we want to this with async/await,
        # we need to trigger the show method

        self.last_route = route

        try:
            from browser import window
        
            window.location.hash = route
        except ImportError as e:
            pass

        self.show(route)

    def show(self, route):
        if route and route[0] == '#':
            route = route[1:]

        self.last_route = route

        if not route:
            route = self.default

        page = self.match(route)

        if page:
            if callable(page.handler):
                page.handler(page.params)
            else:
                page.handler.show(page.params)
        else:
            self.match('not-found').handler(route = route)
        self.trigger('change')

    def match(self, route):
        # match static

        for page in self.static_routes:
            if page.route == route:
                return ODict(handler=page.handler)
        
        for page in self.dynamic_routes:
            matches = re.match(page.expression, route)

            if matches and len(matches.groups()) == len(page.param_keys) - 1:
                return ODict(handler=handler, params=ODict(
                    param: matches.groups()[i]
                    for i, param in enumerate(page.param_keys)
                ))
    
    def get_route_string(self):
        try:
            from browser import window

            route = window.location.hash
            if route and route[0] == '#':
                route = route[1:]
        except ImportError:
            pass
