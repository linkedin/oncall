#!/usr/bin/env python
# -*- coding:utf-8 -*-
from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.util import force_decode
from sphinx.util.compat import Directive
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.docstrings import prepare_docstring
from sphinx.pycode import ModuleAnalyzer

from sphinxcontrib import httpdomain
from sphinxcontrib.autohttp.common import (
    import_object as autohttp_import_object,
    http_directive as autohttp_http_directive
)


def get_routes(app):
    # deep first tree walk on routing tree
    walk_queue = [node for node in app._router._roots]
    while walk_queue:
        curr_node = walk_queue.pop(0)

        if curr_node.method_map:
            for method in curr_node.method_map:
                handler = curr_node.method_map[method]
                try:
                    if handler.__getattribute__('func_name') == 'method_not_allowed':
                        # method not defined for route
                        continue
                except:
                    pass
                yield method, curr_node.uri_template, handler

        if curr_node.children:
            walk_queue = [chl_node for chl_node in curr_node.children] + walk_queue


class AutofalconDirective(Directive):
    has_content = True
    required_arguments = 1

    def make_rst(self, section_title_set):
        # print('importing falcon app %s...' % self.arguments[0])
        app = autohttp_import_object(self.arguments[0])
        for method, path, handler in get_routes(app):
            docstring = handler.__doc__
            if not isinstance(docstring, str):
                analyzer = ModuleAnalyzer.for_module(handler.__module__)
                docstring = force_decode(docstring, analyzer.encoding)
            if not docstring and 'include-empty-docstring' not in self.options:
                continue
            if not docstring:
                continue
            docstring = prepare_docstring(docstring)

            # generate section title if needed
            if path.startswith('/api'):
                section_title = '/'.join(path.split('/')[0:4])
            else:
                section_title = path
            if section_title not in section_title_set:
                section_title_set.add(section_title)
                yield section_title
                yield '_' * len(section_title)

            for line in autohttp_http_directive(method, path, docstring):
                yield line

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        section_title_set = set()
        for line in self.make_rst(section_title_set):
            result.append(line, '<autofalcon>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    if 'http' not in app.domains:
        httpdomain.setup(app)
    app.add_directive('autofalcon', AutofalconDirective)
