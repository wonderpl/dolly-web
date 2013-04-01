from webassets.filter import Filter
from webassets.filter import register_filter
class AJSTemplates(Filter):
    name = 'ajstemplates'

    def output(self, _in, out, **kwargs):
        template = 'angular.module("Weblight").run(["$templateCache", function($templateCache) {\n %s \n}]);\n' % _in.read()
        out.write(template)

    def input(self, _in, out, **kwargs):
        # file name
        temp_array = kwargs['source'].split('/')
        template_name = temp_array[len(temp_array)-1]
        cleaned = _in.read().replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' " + \n " ')
        compiled_template = '\n  $templateCache.put("%s",\n    "%s"\n  );\n' % (template_name, cleaned)
        out.write(compiled_template)

register_filter(AJSTemplates)
