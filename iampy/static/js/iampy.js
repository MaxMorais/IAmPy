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


function attr(t, attr) {
    return t.hasAttribute(attr) ? t.getAttribute(attr) : null;
}

function attr_bool(t, attr) {
    return t.hasAttribute(attr);
}

function attr_str_or_bool(t, attr) {
    if (t.hasAttribute(attr) && !this.getAttribute(attr).length) return true;
    let value = t.getAttribute(attr).trim().toLowerCase();
    return ['true', 'false'].includes(value) ? JSON.parse(value) : value;
}


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
            if (typeof (template) === 'string') {
                let pattern = /<\%\=\sinclude\(\"([a-zA-Z_]+)\"\)\s\%\>/gi,
                    matches = Array.from(template.match(pattern) || []),
                    item,
                    fn;
                while (matches.length) {
                    item = matches.shift();
                    fn = item.split('"')[1];

                    if (typeof (this[fn]) === 'function') template = template.replace(item, this[fn]());

                    Array.from(template.match(pattern)).forEach(match => {
                        if (!matches.includes(match)) matches.push(match);
                    });
                }
            }
            template = tmpl(template, this);
            this.root.innerHTML = template;
        }
    }
    _setEvents() {
        this._elemChilds().forEach(child => {
            this._eventsOf(child).forEach(it => {
                child.addEventListener(it.event, e => {
                    e.stopImmediatePropagation();
                    this._callMethod(it.callback, e);
                });
            });
        });
    }
    _unsetEvents() {
        this._elemChilds().forEach(child => {
            if (!child || !child.parentNode) return;
            //this._eventsOf(child).forEach(it => {
                child.parentNode.replaceChild(child.cloneNode(true), child);
            //});
        });
    }
    _elemChilds(parent = this.root) {
        let childs = [parent];
        if (!parent.childNodes || !parent.childNodes.length) return childs;
        
        Array.from(parent.childNodes).forEach(child => {
            childs = childs.concat(this._elemChilds(child));
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
        return this[name].call(this, ...args);
    }
    connectedCallback() {
        this._initData();
        this.created();
        this._render();
        this.rendered();
    }
    disconnectedCallback(e) {
        e.stopImmediatePropagation();
        this._unsetEvents();
        this.destroyed();
    }
    attributeChangeCallback(attr, old, current) {
        console.log({ attr, old, current });
    }
    created() { }
    rendered() { }
    destroyed() {}
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
    static attach(tag, definition, extend) {
        if (!tag || tag === "") throw new Error("Component tag must be provided");
        window.customElements.define(tag, definition, extend ? {'extends': extend} : {});
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
            this._initDataForm();
        }
    }

    _initDataList() {
        if (!this._storage.has(`List/${this.doctype}`)) {
            let me = this;
            this.client.get(`/api/resource/${this.doctype}`).then(json => {
                me._storage.set(`List/${this.doctype}`, json);
                me.data = json;
                me._unsetEvents()
                me._render();
                me.rendered();
            });
        } else {
            this.data = this._storage.get(`List/${this.doctype}`);
        }
    }

    _initDataForm() {
        if (!this.docname) {
            // new record
            let doc = {
                doctype: this.doctype,
                name: Math.random().toString(36).substr(3),
                __saved: false
            };
            this._storage.set(`${this.doctype}/${doc.name}`, doc);
            this.data = new Data(doc, change => this._dataHandler(change));
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
        return this._schemas.get(this.doctype) || {fields: []};
    }

    get client() {
        if (!this._client) this._client = new JSONRESTClient();
        return this._client;
    }

    get url() {
        return (!this.docname) ? `/api/resource/${this.doctype}` : `/api/resource/${this.doctype}/${this.docname}`;
    }

    get doctype() {
        if (!this._doctype) this._doctype = this.getAttribute("doctype");
        return this._doctype;
    }

    set doctype(value) {
        this._doctype = value
    }

    get docname() {
        if (!this._docname) this._docname = this.getAttribute("docname");
        return this._docname;
    }

    set docname(value) {
        this._docname = value;
    }
    
    get local() {
        return JSON.parse(this.getAttribute("local") || "false");
    }

    get view() {
        if (!this._view) this._view = this.getAttribute("view") || "page";
        return this._view;
    }

    set view(value) {
        this._view = value;
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
                            <a href="#" class="btn btn-primary sm-inline-block btn-icon btn-new" on:click="create">
                                <i class="ti ti-plus"></i> <span class="d-sm-none"> Create new <%= doctype %></span>
                            </a>
                            <% } else { %>
                            <a href="#" class="btn btn-primary sm-inline-block btn-icon btn-save" on:click="save">
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
            <% } else  if (view == "form" && !docname) { %>
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
                                <ul class="nav nav-pills card-header-pills">
                                    <li class="nav-item">
                                        <div class="my-2 my-md-0 flex-grow-1 flw-md-grow=0">
                                            <form action="." method="GET">
                                                <div class="input-icon">
                                                    <input type="text" class="form-control form-control-sm search" placeholder="Search..." aria-label="Search in <%= doctype %>" on:change="search">
                                                    <span class="input-icon-addon">
                                                        <i class="ti ti-search"></i>
                                                    </span>
                                                </div>
                                            </form>
                                        </div>
                                    </li>
                                </ul>
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
                                        <% for (let row of (data && data.length ? data : [])) { %>
                                        <tr data-name="<%= row.name %>">
                                            <% for (let docfield of schema.fields.filter(df => schema.keyword_fields.includes(df.fieldname))) { %>
                                            <td data-fieldname="<%= docfield.fieldname %>" class="<% if (["Percent", "Int", "Float", "Currency"].includes(docfield.fieldtype)) { %>text-right<% }%>">
                                                <%= cellDisplay(docfield, row[docfield.fieldname]) %>
                                            </td>
                                            <% } %>
                                            <td>
                                                <div class="btn-group">
                                                    <a href="#" class="btn btn-ghost-primary sm-inline-block btn-icon btn-edit" data-doctype="<%= row.doctype || doctype %>" data-docname="<%= row.name || this.docname %>" on:click="edit">
                                                        <i class="ti ti-pencil"></i>
                                                    </a>
                                                    <a href="#" class="btn btn-ghost-danger sm-inline-block btn-icon btn-delete" data-doctype="<%= row.doctype || doctype %>" data-docname="<%= row.name || this.docname %>" on:click="delete">
                                                        <i class="ti ti-trash"></i>
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

    template_tree() {
        return `
            <div class="container-fluid">
                <div class="row row-cards">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <ul class="nav nav-pills card-header-pills">
                                    <li class="nav-item">
                                        <div class="my-2 my-md-0 flex-grow-1 flw-md-grow=0">
                                            <form action="." method="GET">
                                                <div class="input-icon">
                                                    <input type="text" class="form-control form-control-sm search" placeholder="Search..." aria-label="Search in <%= doctype %>" on:change="search">
                                                    <span class="input-icon-addon">
                                                        <i class="ti ti-search"></i>
                                                    </span>
                                                </div>
                                            </form>
                                        </div>
                                    </li>
                                </ul>
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
                                        <% for (let row of (data && data.length ? data : [])) { %>
                                        <tr data-name="<%= row.name %>" <% if (row.parent) { %>data-parent="<% row.parent %>"<% } %>>
                                            <% for (let docfield of schema.fields.filter(df => schema.keyword_fields.includes(df.fieldname))) { %>
                                            <td data-fieldname="<%= docfield.fieldname %>" class="<% if (["Percent", "Int", "Float", "Currency"].includes(docfield.fieldtype)) { %>text-right<% }%>">
                                                <%= cellDisplay(docfield, row[docfield.fieldname]) %>
                                            </td>
                                            <% } %>
                                            <td>
                                                <div class="btn-group">
                                                    <a href="#" class="btn btn-ghost-primary sm-inline-block btn-icon btn-edit" data-doctype="<%= row.doctype %>" data-docname="<%= row.name %>" on:click="edit">
                                                        <i class="ti ti-pencil"></i>
                                                    </a>
                                                    <a href="#" class="btn btn-ghost-danger sm-inline-block btn-icon btn-delete" data-doctype="<%= row.doctype %>" data-docname="<%= row.name %>" on:click="delete">
                                                        <i class="ti ti-trash"></i>
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
                                <h4><%= doctype %>: <%= docname %></h4>
                            <div>
                            <div class="d-flex">
                                <a href="#" class="btn btn-ghost-danger btn-cancel" on:click="cancel">Cancel</a>
                                <a href="#" class="btn btn-ghost-primary btn-save" on:click="save">Save</a>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <form action="." method="POST">
                            <% let fieldtype; %>
                            <% for (let docfield of schema.fields) { %>
                                <% fieldtype = docfield.fieldtype.toLowerCase().replace(" ", ""); %> 
                            <rav-control-<%= fieldtype %> doctype="<%= doctype %>" docname="<%= docname %>" docfield="<%= docfield.name %>" ></rav-control-<%= fieldtype %>
                            <% } %>
                        </form>
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

    _changeView(doctype, docname, view='page') {
        debugger;
        this._unsetEvents();

        this.doctype = doctype;
        this.docname = docname;
        this.view = view;

        this._render();
    }

    created() {
        this[`created_${this.view}`]();
    }

    created_page() {
        if (!this._schemas.has(this.doctype)) {
            let me = this;
            this.client.get(`/api/resource/DocType/${this.doctype}`).then(json => {
                me._schemas.set(this.doctype, json);
             });
        }
        this.classList.add('page-wrapper');
    }

    created_list() {
        
    }

    created_form() {
    }

    create(event) {
    }

    edit(event) {
        let btn = event.currentTarget;
        this._changeView(btn.dataset.doctype, btn.dataset.docname, 'form');
    }

    delete(event) {
    }

    save(event) {
    }

    search(event) {
    }

    cancel(event) {
    }
}
Element.attach("rest-admin-view", RESTADMINView);

class RAVBaseControl extends Element {
    constructor() {
        super();
        this._schemas = new SchemaCache();
        this._storage = new Cache();
    }

    get doctype() {
        return this.getAttribute('doctype');
    }

    get docfield() {
        return this.getAttribute('docfield');
    }

    get docname() {
        return this.getAttribute('docname');
    }

    get doc() {
        return this._storage.get(`${this.doctype}/${this.docname}`);
    }

    get field() {
        let schema = this._schemas.get(this.doctype),
            field;
        if (schema && schema.fields) {
            field = schema.fields.filter(df => df.name === this.docfield);
            if (field && field.length) {
                field = field[0];
            }
        };
        return field
    }

    get id() {
        let others = Array.from(document.querySelectorAll(`.form-field[data-fieldname="${this.field.fieldname}"]`));
        return `${this.field.fieldname}_${others.length}`;
    }

    get input() {
        this.getElementById(this.id);
    }

    get docValue() {
        return this.doc[this.field.fieldname];
    }

    set docValue(value) {
        this.doc[this.field.fieldname] = value;
    }

    get inputValue() {
        return this.input.value;
    }

    set inputValue(value) {
        this.input.value = value;
    }

    set value(value) {
        this.docValue = value;
        this.inputValue = value;
    }

    display(value) {
        return value
    }

    data() {
        return this.field;
    }
    
    created() {
        this.classList.add(`mb-${this.field.columns || 3}`)
    }

    template() {
        return `
        <% include("templateLabel") %>
        <% include("templateWrapper") %>
        `
    }
    templateLabel() {
        return `
        <% if (field.label) { %><label class="form-label" for="<%= id %>" <% if (field.required) %> required <% } %>>
            <%= field.label %></label>
            <% include("templateLabelDescription") %>
        <% } %>`;
    }

    templateLabelDescription() {
        return '';
    }

    templateWrapper() {
        return `
        <div class="row g-2">
            <div class="col">
                <% include("templateInput") %>
            </div>
            <% include("templateDescription") %>
        </div>
        `;
    }

    templateDescription() {
        return `
        <% if (field.description) %>
        <div class="col-auto align-self-center">
            <span class="form-help" data-bs-toggle="popover" data-bs-placement="top" data-bs-content="<% field.description %>" data-bs-html="true" data-bs-original-title title>?</span>
        </div>
        <% } %>
        `;
    }
}

class RAVControlReadOnly extends RAVBaseControl {
    templateInput() {
        return `<div class="form-control-plaintext" id="<%= id %>"><%= display(value) %></div>`;
    }

}
Element.attach('rav-control-readonly', RAVControlReadOnly);

class RAVBaseControlInput extends RAVBaseControl {
    templateInput() {
        return `<input type="<% inputType %>" class="form-control" name="<%= fieldname %>" id="<%= id %>" value="<% value %>" <% if (field.placeholder) { %>placeholder="<%= field.placeholder %>"<% } %> <% if (field.disabled) { %>disabled<% } %> <% if (field.readonly) { %>readonly<% } %> <% if (field.mask){ %>data-mask="<%= field.mask %>" data-mask-visible="true" <% } %> autocomplete="off">`
    }
}

class RAVControlData extends RAVBaseControlInput {
    get inputType() {
        return 'text';
    }
}
Element.attach('rav-control-data', RAVControlData);

class RAVControlInt extends RAVControlData {
    rendered() {
        this.mask = IMask(
            this.input,
            {
                mask: Number,
                scale: 0,
                signed: true
            }
        );
    }
}
Element.attach('rav-control-int', RAVControlInt);

class RAVControlIntPositive extends RAVControlInt {
    rendered() {
        this.mask = IMask(
            this.input,
            {
                mask: Number,
                scale: 0,
                signed: false
            }
        );
    }
}
Element.attach('rav-control-intpositive', RAVControlIntPositive);

class RAVControlFloat extends RAVControlInt {
    rendered() {
        this.mask = IMask(
            this.input,
            {
                mask: Number,
                scale: this.field.precision,
                padFractionalZeros: true,
                normalizeZeros: true
            }
        )
    }
}
Element.attach('rav-control-float', RAVControlFloat);

class RAVControlFloatPositive extends RAVControlFloat {
    rendered() {
        this.mask = IMask(
            this.input,
            {
                mask: Number,
                scale: this.field.precision,
                padFractionalZeros: true,
                normalizeZeros: true,
                signed: false
            }
        )
    }
}
Element.attach('rav-control-floatpositive', RAVControlFloatPositive);

class RAVControlCurrency extends RAVControlFloat {
}
Element.attach('rav-control-currency', RAVControlCurrency);

class RAVControlPassword extends RAVBaseControlInput {
    get inputType() {
        return 'password';
    }

    templateInput() {
        let template = super.templateInput();
        return `
        <div class="input-group mb-2">
            ${template}
            <button class="btn" type="button" on:click="togglePassword">
                <i class="ti ti-eye" id="<%= id %>_toggleIcon"></i>
            </button>
        </div>
        `;
    }

    togglePassword(event) {
        let icon = this.getElementById(`${this.id}_toggleIcon`)

        switch (this.input.type) {
            case ("password"):
                this.input.setAttribute("type", "text");
                icon.classList.remove('ti-eye');
                icon.classList.add('ti-eye-off');
                break;
            default:
                this.input.setAttribute("type", "password");
                icon.classList.remove("ti-eye-off");
                icon.classList.add("ti-eye");
                break;
        }
    }
}
Element.attach('rav-control-password', RAVControlPassword);

class RAVControlDate extends RAVBaseControlInput {
    get inputType() {
        return 'text';
    }

    get inputIcon() {
        return 'calendar';
    }
    templateInput() {
        let template = super.templateInput();
        return `
        <div class="input-icon mb-2">
            ${template}
            <span class="input-icon-addon">
                <i class="ti ti-<% inputIcon %>"></i>
            </span>
        </div>
        `
    }
    rendered() {
        this._picker = flatpickr(this.input, {})
    }
}
Element.attach('rav-control-date', RAVControlDate);

class RAVControlDateTime extends RAVControlDate {
    get inputIcon() {
        return 'calendar-time';
    }
    rendered() {
        this._picker = flatpickr(this.input, {
            enableTime: true
        });
    }
}
Element.attach('rav-control-datetime', RAVControlDateTime);

class RAVControlDateRange extends RAVControlDate {
    rendered() {
        this._picker = flatpickr(this.input, {
            mode: 'range'
        });
    }
}
Element.attach('rav-control-daterange', RAVControlDateRange);

class RAVControlTime extends RAVControlDate {
    get inputIcon() {
        return 'clock';
    }
    rendered() {
        this._picker = flatpickr(this.input, {
            enableTime: true,
            noCalendar: true,
            time_24hr: true
        });
    }
}
Element.attach('rav-control-time', RAVControlTime);


class RAVControlRadio extends RAVBaseControlInput {
    get inputType() {
        return 'radio';
    }
}
Element.attach('rav-control-radio', RAVControlRadio);


class RAVControlCheckbox extends RAVBaseControlInput {
    get inputType() {
        return 'checkbox';
    }
}
Element.attach('rav-control-check', RAVControlCheckbox);

class RAVControlFile extends RAVBaseControlInput {
    get inputType() {
        return 'file';
    }
}
Element.attach('rav-control-attach', RAVControlFile);
class RAVControlTextarea extends RAVBaseControlInput {
    get size() {
        return (this.input.value || "").length;
    }
    templateLabelDescription() {
        return `<span class="form-label-description" id="<%= id %>_Counter"><%= size %>/<%= field.length %>`;
    }
    templateInput() {
        return `
        <textarea  class="form-control" name="<%= fieldname %>" id="<%= id %>" <% if (field.placeholder) { %>placeholder="<%= field.placeholder %>"<% } %> <% if (field.disabled) { %>disabled<% } %> <% if (field.readonly) { %>readonly<% } %> on:keyup="handleCounter">
            <% display(value) %>
        </textarea>
        `;
    }

    handleCounter(event) {
        let labelDescription = this.getElementById(`${this.id}_Counter`);
        labelDescription.clear();
        labelDescription.appendChild(document.createTextNode(`${this.size} / ${this.field.length}`))
    }
}
Element.attach('rav-control-smalltext', RAVControlTextarea);

class RAVControlText extends RAVControlTextarea {}
Element.attach('rav-control-text', RAVControlText);

class RAVControlSelect extends RAVBaseControlInput {
    get multiple() {
        return false;
    }
    templateInput() {
        return `
        <select class="form-select" name="<%= fieldname %>" id="<%= id %>" value="<% value %>" <% if (field.placeholder) { %>placeholder="<%= field.placeholder %>"<% } %> <% if (field.disabled) { %>disabled<% } %> <% if (field.readonly) { %>readonly<% } %> <% if (multiple) { %>multiple<% } %>>
            <% for(var option of options){ %>
                <option value="<% option.value %>" <% if (this.value === option.value) { %>selected<% } %>><% option.label %></option>
            <% } %>
        </select>
        `;
    }
}
Element.attach('rav-control-select', RAVControlSelect);

class RAVControlSelectMultiple extends RAVControlSelect {
    get multiple() {
        return true;
    }
}
Element.attach('rav-control-selectmultiple', RAVControlSelectMultiple);

class RAVControlSelectGroup extends RAVControlSelect {
    get inputType() {
        return (!this.multiple) ? 'radio' : 'checkbox';
    }
    template() {
        return `
        <div class="form-selectgroup">
            <% for (var options of options) { %>
            <label class="form-selectgroup-item">
                <input type="<% inputType %>" class="form-selectgroup-input" name="<%= fieldname %>" id="<%= id %>" value="<% value %>" <% if (field.placeholder) { %>placeholder="<%= field.placeholder %>"<% } %> <% if (field.disabled) { %>disabled<% } %> <% if (field.readonly) { %>readonly<% } %> autocomplete="off">
            </label>
            <% } %>
        </div>
        `;
    }
}
Element.attach('rav-control-selectgroup', RAVControlSelectGroup);

class RAVControlSelectGroupMultiple extends RAVControlSelectGroup  {
    get multiple() {
        return true;
    }
}
Element.attach('rav-control-selectgroupmultiple', RAVControlSelectGroupMultiple);