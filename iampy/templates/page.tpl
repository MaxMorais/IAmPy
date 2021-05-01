%setdefault("page_title", "DocType")
%rebase("base.tpl")
<div class="wrapper">
    <aside class="navbar navbar-vertical navbar-expand-lg navbar-dark"></aside>
    <header class="navbar navbar-expand-md navbar-light d-none d-lg-flex d-print-none">
        <div class="container-fluid">
            <div class="d-flex flex-column flex-md-row flex-fill align-items-stretch align-items-md-center">
                <ul class="navbar-nav">
                    <li class="nav-item active">
                        <a class="nav-link" href="#">
                            <span class="nav-link-icon d-md-none d-lg-inline-block">
                                <i class="ti ti-table"></i>
                            </span>
                            <span class="nav-link-title">DocType</span>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#">
                            <span class="nav-link-icon d-md-none d-lg-inline-block">
                                <i class="ti ti-file"></i>
                            </span>
                            <span class="nav-link-title">DocType : FieldType</span>
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </header>
    <rest-admin-view doctype="DocType"></rest-admin-view>
</div>