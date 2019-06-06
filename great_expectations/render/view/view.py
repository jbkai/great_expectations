import json

from jinja2 import (
    Template, Environment, BaseLoader, PackageLoader, select_autoescape
)

class NoOpTemplate(object):
    @classmethod
    def render(cls, model):
        return model

class PrettyPrintTemplate(object):
    @classmethod
    def render(cls, model, indent=2):
        print(json.dumps(model), indent=indent)


class View(object):
    """Defines a method for converting a model to human-consumable form"""

    _template = NoOpTemplate

    @classmethod
    def render(cls, model, template=None):
        if template is None:
            template = cls._template

        t = cls._get_template(template)
        return t.render(model)

    @classmethod
    def _get_template(cls, template):
        if template is None:
            return NoOpTemplate
    
        env = Environment(
            loader=PackageLoader(
                'great_expectations',
                'render/view/templates'
            ),
            autoescape=select_autoescape(['html', 'xml'])
        )
        return env.get_template(template)

class EVRView(View):
    pass

class ExpectationsView(View):
    pass

class DataProfileView(View):
    pass

class ColumnHeaderView(View):
    _template = "header.j2"


class ValueListView(View):
    @classmethod
    def _get_template(cls, template="value_list.j2"):
        return super(ValueListView, cls)._get_template(template)

class ColumnSectionView(View):
    @classmethod
    def _get_template(cls, template="section.j2"):
        return super(ColumnSectionView, cls)._get_template(template)

class PageView(View):
    _template = "page.j2"


class DescriptivePageView(PageView):
    pass