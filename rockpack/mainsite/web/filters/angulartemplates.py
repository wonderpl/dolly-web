from webassets.filter import Filter, register_filter


# FIX: empty files will not be named correctly.
class AJSTemplates(Filter):
    name = ''
    module_name = ''

    def output(self, _in, out, **kwargs):
        template = 'angular.module("' + self.module_name + '").run(["$templateCache", function($templateCache) {\n %s \n}]);\n' % _in.read()
        out.write(template)

    def input(self, _in, out, **kwargs):
        # file name
        temp_array = kwargs['source_path'].split('/')
        template_name = temp_array[len(temp_array) - 1]
        cleaned = _in.read().replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' " + \n " ')
        compiled_template = '\n  $templateCache.put("%s",\n    "%s"\n  );\n' % (template_name, cleaned)
        out.write(compiled_template)


class WebLiteTemplates(AJSTemplates):
    name = 'weblitetemplates'
    module_name = 'WebLite'
register_filter(WebLiteTemplates)


class BookmarkletTemplates(AJSTemplates):
    name = 'bmtemplates'
    module_name = 'Bookmarklet'
register_filter(BookmarkletTemplates)


class FullWeb(AJSTemplates):
    name = 'fullweb'
    module_name = 'WebApp'
register_filter(FullWeb)


class FrontTemplates(AJSTemplates):
    name = 'fronttemplate'
    module_name = 'contentApp'
register_filter(FrontTemplates)
