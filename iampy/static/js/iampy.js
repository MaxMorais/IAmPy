// Simple JavaScript Templating
// John Resig - https://johnresig.com/ - MIT Licensed
(function(){
    var cache = {};
     
    this.tmpl = function tmpl(str, data){
      // Figure out if we're getting a template, or if we need to
      // load the template - and be sure to cache the result.
        var fn = !/\W/.test(str) ?
            cache[str] = cache[str] ||
            tmpl(document.getElementById(str).innerHTML) :
        
            // Generate a reusable function that will serve as a template
            // generator (and which will be cached).
            new Function("obj",
                "var p=[],print=function(){p.push.apply(p,arguments);};" +
        
                // Introduce the data as local variables using with(){}
                "with(obj){p.push('" +
        
                // Convert the template into pure JavaScript
                str
                    .replace(/[\r\t\n]/g, " ")
                    .split("<%").join("\t")
                    .replace(/((^|%>)[^\t]*)'/g, "$1\r")
                    .replace(/\t=(.*?)%>/g, "',$1,'")
                    .split("\t").join("');")
                    .split("%>").join("p.push('")
                    .split("\r").join("\\'")
                + "');}return p.join('');");
        // Provide some basic currying to the user
        return data ? fn( data ) : fn;
    
    };
})();


class Data {
    constructor(target, callback) {
        return Data._observable(target, callback)
    }
    static _observable(target, callback) {
        let self = this,
            handler = (parents = []) => {
                return {
                    get(target, prop) {
                        let current = target[prop];
                        if (typeof current === "object" && current !== null) {
                            return new Proxy(current, handler([...parents, prop]));
                        }
                        return current;
                    },
                    set(target, prop, value) {
                        let props = [...parents, prop],
                            last = target[prop];
                        
                        res = Reflect.set(target, prop, value);
                        callback.call(self, { props, value, last });
                        return res;
                    }
                }
            };
        return new Proxy(target, handler());
    }
    static _props(data) {
        let getProps = obj => {
            let res = [];
            Object.keys(obj).forEach(attr => {
                let value = obj[attr];
                res.push([attr]);
                if (typeof value === "object" && obj[attr] !== null) {
                    getProps(value).forEach(props => {
                        res.push([attr, ...props]);
                    })
                }
            });
            return res;
        }
        return getProps(data);
    }
    static includes(data, props) {
        let included = false;
        Data._props(data).forEach(prop => {
            if (props.every(candidate => prop.includes(candidate))) {
                included = true;
                return
            }
        });
        return included
    }
}

const _eventPrefix = "on:";

class Element extends HTMLElement {
    constructor() {
        super();

        this._watched = {};
        this._initData();
    }
    _initData() {
        let data = this.data();
        if (data) this.data = new Data(data, change => this._dataHandler(change));
    }
    _dataHandler(change) {
        this._render();
        let prop = change.props.join(".");
        if (Object.keys(this._watched).includes(props)) {
            let f = this._watched[prop];
            f.call(this, prop, change.value, change.last);
        }
    }
    _render() {
        this._initRoot();
        this._renderBody();
        this._renderStyles();
        this._setEvents();
    }
    _initRoot() {
        if (this.withShadowRoot) {
            this.attachShadow({ mode: "open" });
            this.root = this.shadowRoot;
        } else {
            this.root = this;
        }
        this.root.innerHTML = "";
    }
    _renderStyles() {
        let styles = this._callMethod("styles");
        if (styles) {
            let style = document.createElement("style");
            style.innerHTML = styles;
            this.root.appendChild(style);
        }
    }
    _renderBody() {
        let template = this._callMethod("template");
        if (template) {
            template = tmpl(template, this);
            this.root.innerHTML = template;
        }
    }
    _setEvents() {
        this._elemChilds().forEach(child => {
            this._eventsOf(child).forEach(it => {
                child.addEventListener(it.event, e => {
                    this._callMethod(it.callback, e);
                });
            });
        });
    }
    _elemChilds(parent = this.root) {
        let childs = [parent];
        if (!parent.childNodes || !parent.childNodes.length) return childs;
        
        Array.from(parent.childNodes).forEach(child => {
            childs = [...childs, ...this._elemChilds(childs)];
        });
        return childs
    }
    _eventsOf(node, prefix = _eventPrefix) {
        if (!node.attributes || !node.attributes.length) return [];
        return Array.from(node.attributes)
            .filter(attr => attr.name.startsWith(prefix))
            .map(attr => {
                return {
                    event: attr.name.replace(prefix, ""),
                    callback: attr.value
                }
            });
    }
    _callMethod(name, ...args) {
        if (typeof this[name] !== "function") return null;
        return this[name].call(this, args);
    }
    connectedCallback() {
        this.created();
        this._render();
        this.rendered();
    }
    disconnectedCallback() {
        this.destroyed();
    }
    attributeChangeCallback(attr, old, current) {
        console.log({ attr, old, current });
    }
    created() { }
    rendered() { }
    destroyed() { }
    props() { return {} }
    data() { return {} }
    template() { return "" }
    style() { return "" }
    watch(prop, handler) {
        let props = prop.split(".");
        if (!Data.includes(this.data, props)) {
            throw new Error(`Element "${this.prototype.constructor.name}" data property "${prop}" can"t be observed because it is not defined.`)
        }
        this._watched[prop] = handler;
    }
    static attach(tag, definition) {
        if (!tag || tag === "") throw new Error("Component tag must be provided");
        window.customElements.define(tag, definition);
    }
}


class RESTClient {
    constructor(config = {}) {
        this.config = config;
        this.middlewares = [];

    }

    _createRequest(url, options, method, data) {
        options = Object.assign({}, this.config, options || {});

        let defaultMethod = !data && options.body ? "GET" : "POST";

        options.method = method || options.method || defaultMethod;

        if (!!data) {
            if (typeof data === "string"
                || RESTClient.isFormData(data)
                || RESTClient.isURLSearchParams(data)
                || RESTClient.isBlob(data)) {
                options.body = data;
            } else {
                try {
                    options.body = JSON.stringify(data);
                } catch(e) {
                    options.body = data;
                }
            }
        }

        return new Request(url, options);

    }

    _request(urlOrRequest, ...options) {
        let request = urlOrRequest instanceof Request ? urlOrRequest : this._createRequest(urlOrRequest, ...options),
            promise = Promise.resolve(request),
            chain = [fetch, undefined];
        
        for (let middleware of this.middlewares.reverse()) {
            chain.unshift(middleware.request, middleware.requestError);
            chain.push(middleware.response, middleware.responseError);
        }

        while (!!chain.length) {
            promise = promise.then(chain.shift(), chain.shift());
        }

        return promise;

    }

    addMiddlewares(middlewares) {
        this.middlewares.push(...middlewares);
    }

    clearMiddlewares() {
        this.middlewares = [];
    }

    fetch(url, options) {
        return this._request(url, options);
    }

    get(url, options) {
        return this._request(url, options, "GET");
    }

    post(url, data, options) {
        return this._request(url, options, "POST", data);
    }

    put(url, data, options) {
        return this._request(url, options, "PUT", data);
    }

    delete(url, options) {
        return this._request(url, options, "DELETE");
    }

    head(url, options) {
        return this._request(url, options, "HEAD");
    }


    static isFormData(obj) {
        return toString.call(obj) === "[object FormData]";
    }

    static isURLSearchParams(obj) {
        return toString.call(obj) === "[object URLSearchParams]";
    }

    static isBlob(obj) {
        return toString.call(obj) === "[object Blob]";
    }
}

class JSONRESTClient extends RESTClient {
    constructor(config){
        super(config);
        this.addMiddlewares([{
            response(res) {
                return res.json().catch(e => {
                    return e
                })
            }
        }]);
    }
}


class Cache {
    constructor() {
        this._storage = localStorage
    }
    set(key, value) {
        this._storage.setItem(key, JSON.stringify(value));
        return value;
    }
    get(key) {
        if (!this.has(key)) return;
        let value = this._storage.getItem(key);
        if (typeof value !== 'string') return;
        try {
            return JSON.parse(value);
        } catch (e) {
            return value;
        }
    }
    has(key) {
        let value = this._storage.getItem(key);
        return Boolean(value && value.length);
    }
    remove(key) {
        if (this.has(key)) this._storage.removeItem(key);
    }
    clear() {
        this._storage.clear();
    }
    items() {
        let ret = [], key;
        for (key of this.keys()){
            ret.push([key, this.get(key)]);
        }
        return ret;
    }
    keys() {
        let ret = [];
        for (let i = 0, j = this._storage.length; i < j; i++){
            ret.push(this._storage.key(i));
        }
        return ret;
    }
    values() {
        let ret = [], key;
        for (key of this.keys()) {
            ret.push(this.get(key));
        }
        return ret;
    }
}

class SchemaCache extends Cache {
    set(key, value) {
        return super.set(`DocType/${key}`, value);
    }
    get(key) {
        return super.get(`DocType/${key}`);
    }
    has(key) {
        if (!key.startsWith('DocType/')) key = `DocType/${key}`;
        return super.has(key);
    }
    remove(key) {
        super.remove(`DocType/${key}`);
    }
}


class RESTADMINView extends Element {
    constructor() {
        super();
        this._schemas = new SchemaCache();
    }

    _initData() {
        this._storage = new Cache();
        if (this.view == 'list') {
            this._initDataList();
        } else if (this.view == 'form') {
            this._initDataRecord();
        }
    }

    _initDataList() {
        if (!this._storage.has(`List/${this.doctype}`)) {
            let me = this;
            this.client.get(`/api/resource/${this.doctype}`).then(json => {
                me._storage.set(`List/${this.doctype}`, json);
                me.data = json;
            });
        } else {
            this.data = this._storage.get(`List/${this.doctype}`);
        }
    }

    _initDataRecord() {
        if (!this.docname) {
            // new record
            this.data = new Data({
                doctype: this.doctype
            }, change => this._dataHandler(change));
        } else {
            // existing record
            let me = this;
            this.client.get(`/api/resource/${this.doctype}/${this.docname}`).then(json => {
                me._storage.set(`${me.doctype}/${me.docname}`, json);
                me.data = new Data(json, change => this._dataHandler(change));
            });
        }
    }

    get schema() {
        return this._schemas.get(this.doctype) || {fields: {}};
    }

    get client() {
        if (!this._client) this._client = new JSONRESTClient();
        return this._client;
    }

    get url() {
        return (!this.docname) ? `/api/resource/${this.doctype}` : `/api/resource/${this.doctype}/${this.docname}`;
    }

    get doctype() {
        return this.getAttribute("doctype");
    }

    get docname() {
        return this.getAttribute("docname");
    }
    
    get local() {
        return JSON.parse(this.getAttribute("local") || "false");
    }

    get view() {
        return this.getAttribute("view") || "page";
    }

    template() {
        return this[`template_${this.view}`]();
    }

    template_page() {
        return `
        <div class="container-fluid">
            <div class="page-header d-print-none">
                <div class="row align-items-center">
                    <div class="col">
                        <% if (docname) { %>
                        <div class="page-pretitle"><%= doctype %></div>
                        <% } %>
                        <div class="page-title"><%= docname || doctype %></div>
                    </div>
                    <div class="col-auto ms-auto d-print-none">
                        <div class="btn-list">
                            <% if (view == "page") { %>
                            <a href="#" class="btn btn-primary sm-inline-block btn-icon btn-new">
                                <i class="ti ti-plus"></i> <span class="d-sm-none">Create new <%= doctype %></span>
                            </a>
                            <% } else { %>
                            <a href="#" class="btn btn-primary sm-inline-block btn-icon btn-save">
                                <i class="ti ti-device-floppy"></i> <span class="d-sm-none">Save</span>
                            </a>
                            <% } %>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="page-body">
            <% if (view == "page") { %>
            <rest-admin-view doctype="<%= doctype %>" view="list"></rest-admin-view>
            <% } else  if (!docname) { %>
            <rest-admin-view doctype="<%= doctype %>" view="form"></rest-admin-view>
            <% } else { %>
            <rest-admin-view doctype="<%= doctype %>" docname="<%= docname %>" view="form"></rest-admin-view>
            <% } %> 
        </div>
        `;
    }

    template_list() {
        return `
            <div class="container-fluid">
                <div class="row row-cards">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                            </div>
                            <div class="table-responsive">
                                <table class="table card-table table-vcenter table-nowrap table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <% for (let docfield of schema.fields.filter(df => schema.keyword_fields.includes(df.fieldname))) { %>
                                            <th data-fieldname="<%= docfield.fieldname %>" class="<% if (["Percent", "Int", "Float", "Currency"].includes(docfield.fieldtype)) { %>text-right<% }%>">
                                                <%= docfield.label %>
                                            </th>
                                            <% } %>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <% for (let row of data) { %>
                                        <tr data-name="<%= row.name %>">
                                            <% for (let docfield of schema.fields.filter(df => schema.keyword_fields.includes(df.fieldname))) { %>
                                            <td data-fieldname="<%= docfield.fieldname %>" "<% if (["Percent", "Int", "Float", "Currency"].includes(docfield.fieldtype)) { %>text-right<% }%>">
                                                <%= cellDisplay(docfield, row[docfield.fieldname]) %>
                                            </td>
                                            <% } %>
                                            <td>
                                                <div class="btn-group">
                                                    <a href="#" class="btn btn-ghost-primary sm-inline-block btn-icon btn-edit" data-doctype="<%= row.doctype %>" data-docname="<%= row.docname %>">
                                                        <i class="ti ti-pencil"></i>
                                                    </a>
                                                    <a href="#" class="btn btn-ghost-danger sm-inline-block btn-icon btn-delete" data-doctype="<%= row.doctype %>" data-docname="<%= row.docname %>">
                                                        <i class="ti ti-plus"></i>
                                                    </a>
                                                </div>
                                            </td>
                                        </tr>
                                        <% } %>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    template_form() {
        return `
        <div class="container-fluid">
            <div class="row row-deck row-cards">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <% if (docname) { %>
                                <h4>Edit <%= doctype %> <%= docname %></h4>
                                <% } else { %>
                                <h4>New <%= doctype %></h4>
                                <% } %>
                            <div>
                            <div class="d-flex">
                                <a href="#" class="btn btn-ghost-danger btn-cancel">Cancel</a>
                                <a href="#" class="btn btn-ghost-primary btn-save">Save</a>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    cellDisplay(column, value) {
        switch (column.fieldtype) {
            case ('Check'):
                value = value ? '<i class="ti ti-square-check"></i>' : '<i class="ti ti-square"></i>';
                break;
        }
        return value;
    }

    created() {
        if (!this._schemas.has(this.doctype)) {
            let me = this;
            this.client.get(`/api/resource/DocType/${this.doctype}`).then(json => {
                me._schemas.set(this.doctype, json);
             });
        }
        this.classList.add('page-wrapper');
    }
}


Element.attach("rest-admin-view", RESTADMINView);
